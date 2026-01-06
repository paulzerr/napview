import os
import time
import json
import numpy as np

import NIDRA

from .database_handler import DatabaseHandler, AnalysisResult
from .helpers import configure_logger, ConfigManager

class Analyzer:

    def __init__(self, base_path, mode):

        self.logger = configure_logger(base_path)
        self.logger.info('Analyzer started in mode: << {mode} >>...')

        self.mode             = mode
        self.base_path        = base_path

        # Create a temporary directory for NIDRA output
        self.nidra_output_dir = os.path.join(self.base_path, 'nidra_temp')
        os.makedirs(self.nidra_output_dir, exist_ok=True)

        self.config_manager = ConfigManager(base_path)
        self.config = self.config_manager.load_config(instance=self)

        self.epoch_length = self.config.get('epoch_length', 30)
        
        self.db_handler = DatabaseHandler(self.base_path)
        self.db_handler.setup_database()

        self.eeginfo = self.db_handler.retrieve_info() # TODO: read this from config (only sample rate needed, perhaps channels)
        self.eeginfo.channel_names = json.loads(self.eeginfo.channel_names)


    def _calculate_retrieval_start_index(self, start_idx, end_idx, single_epoch):
        """Calculates the start index for data retrieval."""

        if single_epoch:
            return int(start_idx)

        # For a sliding window, go back up to 20 minutes (1200 seconds) # TODO: set/get from config
        context_duration_seconds = 1200  
        # Calculate start of the window
        start_idx_window = max(0, end_idx - context_duration_seconds * self.eeginfo.sample_rate)
        
        # Align the start index to the beginning of an epoch boundary.
        samples_per_epoch = self.epoch_length * self.eeginfo.sample_rate
        aligned_start_idx = (start_idx_window // samples_per_epoch) * samples_per_epoch
        
        return int(aligned_start_idx)

    def get_data(self, start_idx, end_idx, single_epoch=False):
        """
        Retrieves EEG data for a given time range.
        """
        total_samples = self.db_handler.get_total_n_samples()
        if total_samples is None:
            self.logger.warning(f"Analyzer ({self.mode}): no samples available.")
            return None
        start_idx_max = self._calculate_retrieval_start_index(start_idx, end_idx, single_epoch)
        epoch_data = self.db_handler.retrieve_data(start_idx_max, end_idx)
        return epoch_data.astype(np.float64)

    def volts_to_microvolts(self,data):
        if data is None:
            return None
        if data.ndim == 1:
            median = np.median(data)
            q25 = np.quantile(np.abs(data - median), 0.25)
            m_value = q25
        else:
            medians = np.median(data, axis=1, keepdims=True)
            q25 = np.quantile(np.abs(data - medians), 0.25, axis=1)
            m_value = np.median(q25)
        return data * 1e6 if m_value < 1e-2 else data

    def predict_sleep_stage(self, start_idx, end_idx, timestamp):
        analysis_result = {'timestamp': timestamp}
        results_probabilities = np.zeros(5)
        try:
            all_data_uv = self.volts_to_microvolts(self.get_data(start_idx, end_idx))
            if all_data_uv is None:
                self.logger.warning(f"Analyzer ({self.mode}): No data retrieved for indices {start_idx} to {end_idx}.")
                return None
            
            samples_per_epoch = self.epoch_length * self.eeginfo.sample_rate
            if all_data_uv.shape[-1] < (6 * samples_per_epoch):
                self.logger.warning(
                    f"Analyzer ({self.mode}): Not enough samples yet. Waiting for more data."
                )
                time.sleep(1)
                return None
            
            scorer = NIDRA.scorer(
                type='psg',
                input=all_data_uv,
                output=self.nidra_output_dir,
                channels=self.eeginfo.channel_names,
                sfreq=self.eeginfo.sample_rate,
                hypnogram=False,
                hypnodensity=False,
                plot=False,
            )
            hypno, probs = scorer.score()
            results_probabilities = probs[0, :5]
            
        except Exception as e:
            self.logger.error(f'Analyzer.predict_sleep_stage: Failed during staging process: {e}', exc_info=True)
            results_probabilities = np.zeros(5)

        analysis_result.update({
            'w':   np.nan_to_num(float(results_probabilities[0]), nan=0.0),
            'n1':  np.nan_to_num(float(results_probabilities[1]), nan=0.0),
            'n2':  np.nan_to_num(float(results_probabilities[2]), nan=0.0),
            'n3':  np.nan_to_num(float(results_probabilities[3]), nan=0.0),
            'rem': np.nan_to_num(float(results_probabilities[4]), nan=0.0)
        })
        self.db_handler.add_analysis_result(analysis_result, analyzer_mode=self.mode)

        return analysis_result


    def count_already_analyzed_epochs(self):
        """Counts how many epochs have been analyzed for the current mode."""
        try:
            n_analyzed = AnalysisResult.select().where(AnalysisResult.analyzer_mode == self.mode).count()
            return n_analyzed
        except Exception as e:
            self.logger.error(f"Analyzer ({self.mode}): Could not get number of analyzed epochs. Error: {e}", exc_info=True)
            return 0

    def find_next_epoch_indices(self, number_already_analyzed_epochs):
        """
        Determines the start and end sample indices for the next epoch to be analyzed.
        """
        samples_per_epoch = self.eeginfo.sample_rate * self.epoch_length
        total_n_samples = self.db_handler.get_total_n_samples()

        if total_n_samples is None:
            return None, None, None

        potential_epochs = total_n_samples // samples_per_epoch
        
        if potential_epochs > number_already_analyzed_epochs:
            start_sample_index = number_already_analyzed_epochs * samples_per_epoch
            end_sample_index = start_sample_index + samples_per_epoch - 1
            timestamp = self.db_handler.get_sample_timestamp(start_sample_index)
            return start_sample_index, end_sample_index, timestamp
        else:
            return None, None, None

    def run(self):
        last_epoch_timestamp = 0
        
        current_epoch_index = self.count_already_analyzed_epochs()
        self.logger.info(f"Analyzer ({self.mode}): Beginning analysis from epoch index {current_epoch_index}.")

        if current_epoch_index > 0:
            try:
                # Get the timestamp of the last analyzed epoch to enforce the time delay correctly from the start.
                last_result = AnalysisResult.select().where(AnalysisResult.analyzer_mode == self.mode).order_by(AnalysisResult.timestamp.desc()).get()
                last_epoch_timestamp = last_result.timestamp
                self.logger.info(f"Analyzer ({self.mode}): Last analyzed epoch timestamp is {last_epoch_timestamp}.")
            except Exception as e:
                self.logger.error(f"Analyzer ({self.mode}): Could not get last analyzed epoch timestamp. Error: {e}", exc_info=True)

        while True:
            try:
                start_idx, end_idx, timestamp = self.find_next_epoch_indices(current_epoch_index)
                
                # also check if enough time has passed since the last epoch was analyzed
                if start_idx is not None and (last_epoch_timestamp == 0 or timestamp >= last_epoch_timestamp + self.epoch_length):
                    self.logger.info(f"Analyzer ({self.mode}): Running prediction for epoch {current_epoch_index} at timestamp {timestamp}...")
                    self.predict_sleep_stage(start_idx, end_idx, timestamp)
                    last_epoch_timestamp = timestamp
                    current_epoch_index += 1
                else:
                    # No new full epoch available, wait before checking again.
                    time.sleep(.1)
            except Exception as e:
                self.logger.error(f"Analyzer ({self.mode}): An error occurred in the run loop: {e}", exc_info=True)
                time.sleep(5) # Wait before retrying to avoid rapid failure loops


    def shutdown(self):
        self.logger.info(f"Analyzer ({self.mode}): Shutting down...")
        if self.db_handler:
            self.db_handler.close() 
