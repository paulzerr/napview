from peewee import *
import zlib
import struct
import numpy as np
import time
import os
import json 
import datetime
from functools import wraps

from .helpers import configure_logger, ConfigManager

eeg_db_proxy      = DatabaseProxy()
results_db_proxy  = DatabaseProxy()

class EEGData(Model):
    index     = IntegerField(primary_key=True)
    timestamp = FloatField()
    data      = BlobField()
    class Meta:
        database = eeg_db_proxy
        table_name = 'eeg_data'

class EEGInfo(Model):
    recording_id             = PrimaryKeyField()
    sample_rate              = IntegerField()
    recording_start_time_dt  = DateTimeField()
    recording_start_time_sec = FloatField()
    n_channels               = IntegerField()
    channel_names            = CharField()
    class Meta:
        database = eeg_db_proxy
        table_name = 'eeg_info'

class AnalysisResult(Model):
    timestamp     = FloatField()
    results_data  = TextField()
    analyzer_mode = CharField()
    timestamp_row_update = DateTimeField(default=time.time)
    
    class Meta:
        database = results_db_proxy
        table_name = 'analysis_results'
        primary_key = CompositeKey('timestamp', 'analyzer_mode')



def lex(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return func(self, *args, **kwargs)
        except Exception as e:
            self.logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            return None
    return wrapper

class DatabaseHandler:
    def __init__(self, base_path):
        self.logger = configure_logger(base_path)
        self.logger.info('Database Handler: started...')
        self.eeg_db = None
        self.results_db = None
        self.recording_start_time = None

        self.config_manager = ConfigManager(base_path)
        self.config = self.config_manager.load_config(instance=self)

    def database_exists(self, db_file_path):
        return os.path.exists(db_file_path)

    @lex
    def get_total_n_samples(self):
        return EEGData.select().count()

    @lex
    def get_most_recent_timestamp(self):
        return EEGData.select(fn.MAX(EEGData.timestamp)).scalar()

    @lex
    def get_sample_timestamp(self, sample_index) -> float | None:
        return EEGData.select(EEGData.timestamp).where(EEGData.index == sample_index).scalar()

    def create_unique_db_filename(self, base_path):
        filepath = f"{base_path}/temp/db/eeg_data.db"
        results_filepath = f"{base_path}/temp/db/results_data.db"
        base, ext = os.path.splitext(filepath)
        for i in range(1, 100):
            new_filepath = f"{base}_{i}{ext}"
            if not os.path.exists(new_filepath):
                return new_filepath, results_filepath
        raise ValueError("Cannot create a unique filename.")

    # In DatabaseHandler class:
    def setup_database(self, create_tables=False):
        self.logger.info(f"Setting up database (create_tables={create_tables})...")
        try:
            self.config = self.config_manager.load_config()
            eeg_db_path = None
            results_db_path = None

            if create_tables:
                self.logger.info("Generating new unique database filenames.")
                eeg_db_path, results_db_path = self.create_unique_db_filename(self.base_path)
                self.logger.debug(f"Generated paths: EEG='{eeg_db_path}', Results='{results_db_path}'")
                db_paths_to_save = {
                    'eeg_db_path': eeg_db_path,
                    'results_db_path': results_db_path
                }
                self.config_manager.save_config(db_paths_to_save)
                self.logger.info("Saved new database paths to config.")
            else:
                self.logger.info("Loading database paths from existing config.")
                eeg_db_path = self.config.get('eeg_db_path')
                results_db_path = self.config.get('results_db_path')
                if not eeg_db_path or not results_db_path:
                    self.logger.warning("One or both DB paths are missing from config.")

            if not eeg_db_path or not results_db_path:
                self.logger.error("Cannot proceed: database paths are invalid.")
                return None

            self.logger.debug(f"Initializing EEG DB at: {eeg_db_path}")
            self.eeg_db = SqliteDatabase(eeg_db_path, pragmas={'journal_mode': 'wal', 'synchronous': 'normal', 'foreign_keys': 1})
            
            self.logger.debug(f"Initializing Results DB at: {results_db_path}")
            self.results_db = SqliteDatabase(results_db_path, pragmas={'journal_mode': 'wal', 'synchronous': 'normal', 'foreign_keys': 1})

            eeg_db_proxy.initialize(self.eeg_db)
            results_db_proxy.initialize(self.results_db)
            self.logger.debug("Database proxies initialized.")

            self.eeg_db.connect(reuse_if_open=True)
            self.logger.info(f"EEG DB connection successful.")
            
            self.results_db.connect(reuse_if_open=True)
            self.logger.info(f"Results DB connection successful.")

            if create_tables:
                self.logger.info("Creating new database tables...")
                self.eeg_db.create_tables([EEGData, EEGInfo], safe=True)
                self.results_db.create_tables([AnalysisResult], safe=True)
                self.logger.info("Database tables created successfully.")
            else:
                self.logger.info("Skipping table creation as requested.")

            self.logger.info("Database setup completed successfully.")
            return self.eeg_db, self.results_db

        except Exception as e:
            self.logger.error(f"EXCEPTION during database setup: {e}", exc_info=True)
            # Cleanup logic
            if hasattr(self, 'eeg_db') and self.eeg_db and not self.eeg_db.is_closed():
                self.eeg_db.close()
            if hasattr(self, 'results_db') and self.results_db and not self.results_db.is_closed():
                self.results_db.close()
            eeg_db_proxy.initialize(None)
            results_db_proxy.initialize(None)
            self.logger.debug("Database connections closed and proxies de-initialized due to exception.")
            return None

    @lex
    def create_info_entry(self, recording_id: int, sample_rate: int, n_channels: int,
                           recording_start_time_dt: datetime, recording_start_time_sec: float,
                           channel_names: str):
        EEGInfo.create(
            recording_id=recording_id,
            sample_rate=sample_rate,
            n_channels=n_channels,
            recording_start_time_sec=recording_start_time_sec,
            recording_start_time_dt=recording_start_time_dt,
            channel_names=channel_names
        )
        self.logger.info("Database Handler: EEG amp info created:")
        self.logger.info(f"  Recording ID: {recording_id}")
        self.logger.info(f"  Sample Rate: {sample_rate}")
        self.logger.info(f"  Number of Channels: {n_channels}")
        self.logger.info(f"  Start Time: {recording_start_time_dt}")
        self.logger.info(f"  Channel Names: {channel_names}")

    @lex
    def create_data_entry(self, sample, timestamp, sample_index):
        sample_compressed = zlib.compress(struct.pack(f'{len(sample)}f', *sample))
        EEGData.create(index=sample_index, timestamp=timestamp, data=sample_compressed)

    def add_analysis_result(self, result_dict_in, analyzer_mode):
        timestamp = result_dict_in.get('timestamp')
        if not timestamp or not analyzer_mode:
            self.logger.error("Database Handler: add_analysis_result: 'timestamp' or 'analyzer_mode' invalid/missing.")
            return
        
        data_for_json_storage = json.dumps({
            k: v for k, v in result_dict_in.items()
            if k not in ['timestamp', 'analyzer_mode'] 
        })
        
        AnalysisResult.create(
            timestamp     = timestamp,
            analyzer_mode = analyzer_mode,
            results_data  = data_for_json_storage,
            timestamp_row_update     = time.time()
        )


    def get_all_analysis_results(self, desired_fields: list, analyzer_mode=None):
        results_by_field = {field: [] for field in desired_fields}

        try:
            query = AnalysisResult.select(
                AnalysisResult.timestamp,
                AnalysisResult.results_data
            )
            if analyzer_mode:
                query = query.where(AnalysisResult.analyzer_mode == analyzer_mode)
            query = query.order_by(AnalysisResult.timestamp)

            for record in query:
                timestamp = record.timestamp
                try:
                    epoch_data_dict = json.loads(record.results_data)
                except Exception as e:
                    self.logger.error(f"Database Handler: Error decoding JSON: {e}", exc_info=True)

                for field in desired_fields:
                    if field in epoch_data_dict:
                        value = epoch_data_dict[field]
                        results_by_field[field].append({'x': timestamp, 'y': value})
            return results_by_field
        except Exception as e:
            self.logger.error(
                f"Database Handler: Error retrieving/processing analysis results for fields {desired_fields} "
                f"(mode={analyzer_mode}): {e}",
                exc_info=True
            )
            return {field: [] for field in desired_fields}


    def retrieve_info(self, retries=100):
        for retry_count in range(retries):
            try:
                eeginfo = EEGInfo.get()
                return eeginfo
            except:
                self.logger.warning(f"Database Handler: Database not found. Attempt {retry_count + 1}/{retries}. Waiting 1 second before retrying...")
                time.sleep(1)
        self.logger.error(f"Database Handler: Failed to retrieve EEGInfo after {retries} attempts. Aborting.", exc_info=True)
        return None

    @lex
    def retrieve_data(self, start, end):
        selected_data = EEGData.select().where(
            (EEGData.index >= start) & (EEGData.index <= end)
        ).order_by(EEGData.index)
        self.eeg_info = self.retrieve_info()
        eeg_data = np.array([
            struct.unpack(f'{self.eeg_info.n_channels}f', zlib.decompress(data.data))
            for data in selected_data
        ])
        return eeg_data.T


    def close(self):
        if hasattr(self, 'eeg_db') and self.eeg_db and not self.eeg_db.is_closed():
            self.eeg_db.close()
            self.logger.info('Database Handler: EEG DB connection closed.')
            self.eeg_db = None 
        if hasattr(self, 'results_db') and self.results_db and not self.results_db.is_closed():
            self.results_db.close()
            self.logger.info('Database Handler: Results DB connection closed.')
            self.results_db = None 
