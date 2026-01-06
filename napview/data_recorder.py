import time
from pylsl import resolve_byprop, StreamInlet
from peewee import *
import json
import datetime

from .database_handler import DatabaseHandler
from .helpers import configure_logger, ConfigManager


class DataRecorder:
    def __init__(self, base_path, mode):
        self.base_path = base_path

        # setup communication
        self.logger = configure_logger(self.base_path)
        self.logger.info('Recorder: started...')

        # load variables from config.json
        self.config_manager = ConfigManager(self.base_path)
        self.config = self.config_manager.load_config(instance=self)

        # connect to db
        self.db_handler = DatabaseHandler(self.base_path)
        setup_ok = self.db_handler.setup_database()
        if not setup_ok:
            self.logger.critical(f"Recorder: CRITICAL - Failed to set up database connections. Cannot run.")
            raise ConnectionError("Recorder failed DB setup") 


    def connect_to_lsl_stream(self):
        lsl_connection_attempts = 0
        self.config = self.config_manager.load_config(instance=self)
        lsl_stream_name = self.config.get('lsl_stream_name', 'default_stream_name')

        while True:
            lsl_connection_attempts += 1
            self.logger.info(f"Recorder: Attempting to connect to LSL stream (attempt {lsl_connection_attempts})", exc_info=True)
            streams = None
            properties = [
                ('name', lsl_stream_name),
                ('type', 'EEG'),
                (None, None)
            ]

            for prop, value in properties:
                try:
                    if prop == 'name':
                        self.logger.info(f"Recorder: Looking for stream by name '{value}'")
                        streams = resolve_byprop('name', value, timeout=2.0)
                    elif prop == 'type':
                        self.logger.info(f"Recorder: Looking for stream by type '{value}'")
                        streams = resolve_byprop('type', value, timeout=2.0)
                    else:
                        self.logger.info("Recorder: Looking for any available LSL stream")
                        streams = resolve_byprop(timeout=2.0)
                    if streams:
                        break
                except Exception as e:
                    self.logger.error(f"Recorder: Error finding stream by {prop or 'any'} '{value or ''}': {e}", exc_info=True)

            if streams:
                self.logger.info(f"Recorder: Found streams: '{streams[0]}'")
                self.logger.info(f"Recorder: Connecting to stream: '{lsl_stream_name}'")
                try:
                    self.connect_to_stream(streams[0])
                    break
                except Exception as e:
                    self.logger.error(f"Recorder: Error connecting to stream: {e}", exc_info=True)
            else:
                self.logger.error(f"Recorder: No streams found (attempt {lsl_connection_attempts})", exc_info=True)
                time.sleep(2)

    def connect_to_stream(self, stream):

        self.inlet = StreamInlet(stream)
        stream_info = self.inlet.info()
        stream_name = stream_info.name()
        stream_uid = stream_info.uid()
        self.logger.info(f"Recorder: Connected to LSL stream:")
        self.logger.info(f"  Stream name: {stream_name}")
        self.logger.info(f"  Stream UID: {stream_uid}")

        # Retrieve stream information
        self.sample_rate = stream_info.nominal_srate()
        self.n_channels = stream_info.channel_count()

        # Get the channel names from the description
        description = stream_info.desc()
        self.channel_names = []
        channels = description.child('channels').first_child()
        for _ in range(stream_info.channel_count()):
            self.channel_names.append(channels.child_value('label'))
            channels = channels.next_sibling()



    def reinitialize_inlet(self):
        self.logger.info("Recorder: Attempting to reinitialize LSL inlet...")

        max_retries = 100  # Maximum number of reconnection attempts
        retry_delay = 1  # Delay in seconds between retries
        retries = 0

        while retries < max_retries:
            try:
                # Reload configuration to ensure the latest settings are used
                self.config = self.config_manager.load_config(instance=self)
                lsl_stream_name = self.config.get('lsl_stream_name', 'default_stream_name')

                self.logger.info(f"Recorder: Looking for stream '{lsl_stream_name}'...")
                streams = resolve_byprop('name', lsl_stream_name, timeout=2.0)

                if streams:
                    self.logger.info(f"Recorder: Stream '{lsl_stream_name}' found. Reconnecting...")
                    self.connect_to_stream(streams[0])
                    self.logger.info("Recorder: LSL inlet successfully reinitialized.")
                    return  
                else:
                    self.logger.warning(f"Recorder: Stream '{lsl_stream_name}' not found. Retrying...")
            except Exception as e:
                self.logger.error(f"Recorder: Error during inlet reinitialization: {e}", exc_info=True)

            retries += 1
            time.sleep(retry_delay)

        # If we exhaust retries without success, log a critical error and take action
        self.logger.critical(f"Recorder: Failed to reinitialize LSL inlet after {max_retries} attempts.")
        self.shutdown()  # Gracefully shut down the system


    def receive_data_loop(self):
        self.logger.info("Recorder: Starting to receive data...")
        sample_index = 0
        last_data_received_time = time.time()

        eeg_amp = self.config.get('eeg_amp')
        in_volt = eeg_amp == "customlsl"

        poll_interval = 0.0005  # initial 500 µs poll interval

        while True:
            with self.db_handler.eeg_db.atomic():
                counter = 0
                while counter < 1000:
                    try:
                        chunk, timestamps = self.inlet.pull_chunk()
                        if chunk:
                            last_data_received_time = time.time()
                            for sample, timestamp in zip(chunk, timestamps):
                                if in_volt:
                                    sample = [s / 1e6 for s in sample]

                                timestamp_relative = timestamp - self.recording_start_time_sec

                                self.db_handler.create_data_entry(sample, timestamp_relative, sample_index)
                                counter += 1
                                sample_index += 1
                            poll_interval = max(0.0001, poll_interval * 0.9)
                        else:
                            if time.time() - last_data_received_time > 10:
                                self.logger.warning("Recorder: No data received for more than 5 seconds.")
                                self.reinitialize_inlet()
                                last_data_received_time = time.time()
                            # Adapt poll interval for idle periods
                            poll_interval = min(0.005, poll_interval * 1.1)
                    except Exception as e:
                        self.logger.error(f"Recorder: Error receiving data: {e}", exc_info=True)
                        self.reinitialize_inlet()  # Attempt recovery
                        time.sleep(1)
                time.sleep(poll_interval)

    def shutdown(self):
        self.logger.info("Recorder: Shutting down...")
        if hasattr(self, 'inlet'):
            self.inlet.close_stream()
            self.logger.info("Recorder: LSL inlet closed")
        if hasattr(self, 'db'):
            self.eeg_db.close()
            self.logger.info("Recorder: Database connection closed")
        self.logger.info("Recorder: Shutdown.")

    def run(self):
        try:
            self.recording_start_time_sec = time.perf_counter()
            self.recording_start_time_dt = datetime.datetime.now()
            time.sleep(1)
            self.connect_to_lsl_stream()
            self.logger.info("Recorder: LSL inlet opened")
            self.db_handler.create_info_entry(
                recording_id=1,
                sample_rate=self.sample_rate,
                n_channels=self.n_channels,
                recording_start_time_sec=self.recording_start_time_sec,
                recording_start_time_dt=self.recording_start_time_dt,
                channel_names=json.dumps(self.channel_names)
            )
            self.receive_data_loop()
        except Exception as e:
            self.logger.error(f"Recorder: Error during run: {e}", exc_info=True)
            self.shutdown()
