import os
import math
import time
import json
import numpy as np
import scipy.signal as sp_sig

import NIDRA

from .database_handler import DatabaseHandler, AnalysisResult
from .helpers import configure_logger, ConfigManager
from .yasa_staging_minimal import bandpower_from_psd

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
        self.min_context_seconds = 30
        
        self.db_handler = DatabaseHandler(self.base_path)
        self.db_handler.setup_database()

        self.eeginfo = self.db_handler.retrieve_info() # TODO: read this from config (only sample rate needed, perhaps channels)
        self.eeginfo.channel_names = json.loads(self.eeginfo.channel_names)


    def _calculate_retrieval_start_index(self, start_idx, end_idx):
        """Calculates the start index for data retrieval."""

        # For a sliding window, go back up to 20 minutes (1200 seconds) # TODO: set/get from config
        context_duration_seconds = 1200  
        # Calculate start of the window
        start_idx_window = max(0, end_idx - context_duration_seconds * self.eeginfo.sample_rate)
        
        # Align the start index to the beginning of an epoch boundary.
        samples_per_epoch = self.epoch_length * self.eeginfo.sample_rate
        aligned_start_idx = (start_idx_window // samples_per_epoch) * samples_per_epoch
        
        return int(aligned_start_idx)

    def get_data(self, start_idx, end_idx):
        """Retrieves EEG data from db for a given time range."""
        total_samples = self.db_handler.get_total_n_samples()
        min_required_samples = int(self.min_context_seconds * self.eeginfo.sample_rate)
        if total_samples is None or total_samples < min_required_samples:
            self.logger.warning(f"Analyzer ({self.mode}): Not enough samples yet. Waiting for more data.")
            return None
        start_idx_max = self._calculate_retrieval_start_index(start_idx, end_idx)
        epoch_data = self.db_handler.retrieve_data(start_idx_max, end_idx)
        return self.volts_to_microvolts(epoch_data.astype(np.float64))

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

    def find_next_epoch_indices(self, current_epoch_index):
        """
        Determines the start and end sample indices for the next epoch to be analyzed.
        """
        samples_per_epoch = self.eeginfo.sample_rate * self.epoch_length
        total_n_samples = self.db_handler.get_total_n_samples()

        if total_n_samples is None:
            return None, None, None, False

        potential_epochs = total_n_samples // samples_per_epoch
        
        if potential_epochs > current_epoch_index:
            start_sample_index = current_epoch_index * samples_per_epoch
            end_sample_index = start_sample_index + samples_per_epoch - 1
            timestamp = self.db_handler.get_sample_timestamp(start_sample_index)
            return start_sample_index, end_sample_index, timestamp, True
        else:
            return None, None, None, False


    def predict_sleep_stage(self, epoch_data, timestamp):
        
        try:
            score_start = time.perf_counter()
            scorer = NIDRA.scorer(
                type='psg',
                input=epoch_data,
                output=self.nidra_output_dir,
                channels=self.eeginfo.channel_names,
                sfreq=self.eeginfo.sample_rate,
                hypnogram=False,
                hypnodensity=False,
                plot=False,
            )
            hypno, probs = scorer.score()
            score_elapsed = time.perf_counter() - score_start
            window_seconds = epoch_data.shape[-1] / self.eeginfo.sample_rate
            self.logger.info(
                f"Analyzer ({self.mode}): Sleep staging took {score_elapsed:.3f} s "
                f"on {window_seconds:.1f} s of data."
            )
            results_probabilities = probs[0, :5]
            analysis_result = {'timestamp': timestamp}
            analysis_result.update({
                'w':   np.nan_to_num(float(results_probabilities[0]), nan=0.0),
                'n1':  np.nan_to_num(float(results_probabilities[1]), nan=0.0),
                'n2':  np.nan_to_num(float(results_probabilities[2]), nan=0.0),
                'n3':  np.nan_to_num(float(results_probabilities[3]), nan=0.0),
                'rem': np.nan_to_num(float(results_probabilities[4]), nan=0.0)
            })
            return analysis_result
        except Exception as e:
            self.logger.error(f'Analyzer.predict_sleep_stage: Failed during staging process: {e}', exc_info=True)
            return None

    def compute_bandpower_from_window(self, epoch_data, timestamp):
        try:
            samples_per_epoch = self.epoch_length * self.eeginfo.sample_rate
            epoch_data = epoch_data[..., -samples_per_epoch:]
            win = min(int(5 * self.eeginfo.sample_rate), epoch_data.shape[-1])
            freqs, psd = sp_sig.welch(epoch_data, self.eeginfo.sample_rate, nperseg=win, axis=-1)
            default_bands = [
                (0.5, 4, "delta"),
                (4, 8, "theta"),
                (8, 12, "alpha"),
                (16, 30, "beta"),
                (30, 40, "gamma"),
            ]
            bands_config = self.config.get("bandpower_bands", default_bands)
            bands = [tuple(band) for band in bands_config]
            bp = bandpower_from_psd(psd, freqs, bands=bands, relative=True)
            analysis_result = {'timestamp': timestamp}
            analysis_result.update({
                'delta_power': float(bp['delta'].mean()),
                'theta_power': float(bp['theta'].mean()),
                'alpha_power': float(bp['alpha'].mean()),
                'beta_power': float(bp['beta'].mean()),
                'gamma_power': float(bp['gamma'].mean()),
            })
            return analysis_result
        except Exception as e:
            self.logger.error(f'Analyzer.compute_bandpower: Failed during bandpower process: {e}', exc_info=True)
            return None

    def run(self):
        # this will become useful once we implement persistent storage of analysis results, and restarting the analyzer without losing progress
        #
        # current_epoch_index = AnalysisResult.select().where(AnalysisResult.analyzer_mode == self.mode).count()
        # self.logger.info(f"Analyzer ({self.mode}): Beginning analysis from epoch index {current_epoch_index}.")
        # if current_epoch_index > 0:
        #     try:
        #         # Get the timestamp of the last analyzed epoch to enforce the time delay correctly from the start.
        #         last_result = AnalysisResult.select().where(AnalysisResult.analyzer_mode == self.mode).order_by(AnalysisResult.timestamp.desc()).get()
        #         last_epoch_timestamp = last_result.timestamp
        #         self.logger.info(f"Analyzer ({self.mode}): Last analyzed epoch timestamp is {last_epoch_timestamp}.")
        #     except Exception as e:
        #         self.logger.error(f"Analyzer ({self.mode}): Could not get last analyzed epoch timestamp. Error: {e}", exc_info=True)

        current_epoch_index = max(0, int(math.ceil(self.min_context_seconds / self.epoch_length)) - 1)

        while True:
            time.sleep(1)
            try:
                start_idx, end_idx, _data_timestamp, ready = self.find_next_epoch_indices(current_epoch_index)
                if not ready: # if no full new un-analyzed epoch is available yet
                    continue

                epoch_data = self.get_data(start_idx, end_idx)
                if epoch_data is None: 
                    continue           
                    
                analysis_timestamp = time.time()
                self.logger.info(f"Analyzer ({self.mode}): Running analysis for epoch {current_epoch_index} at timestamp {analysis_timestamp}...")
                staging_result = self.predict_sleep_stage(epoch_data, analysis_timestamp)
                bandpower_result = self.compute_bandpower_from_window(epoch_data, analysis_timestamp)
                if staging_result is None or bandpower_result is None:
                    self.logger.warning(f"Analyzer ({self.mode}): Analysis failed for epoch {current_epoch_index} at timestamp {analysis_timestamp}. Retrying...")
                    continue
                self.db_handler.add_analysis_result(staging_result, analyzer_mode=self.mode)
                self.db_handler.add_analysis_result(bandpower_result, analyzer_mode='bandpower')
                self.logger.info(
                    f"Analyzer ({self.mode}): Analysis saved for epoch {current_epoch_index} at timestamp {analysis_timestamp}."
                )
                current_epoch_index += 1
            except Exception as e:
                self.logger.error(f"Analyzer ({self.mode}): An error occurred in the run loop: {e}", exc_info=True)


    def shutdown(self):
        self.logger.info(f"Analyzer ({self.mode}): Shutting down...")
        if self.db_handler:
            self.db_handler.close() 
