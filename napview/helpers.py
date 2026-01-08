import os
import logging
import json 
import sys
from pathlib import Path
import threading 
import time

def get_resource_root():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent / "napview"
    return Path(__file__).resolve().parent

def configure_logger(base_path, log_filename=None, force=False):
    logger = logging.getLogger('napview_logger')
    try:
        logger.setLevel(logging.DEBUG)
        base_path = Path(base_path) if not isinstance(base_path, Path) else base_path
        base_path.mkdir(parents=True, exist_ok=True)

        if log_filename is None:
            config_path = base_path / "config.json"
            if config_path.exists():
                with open(config_path, 'r') as config_file:
                    config = json.load(config_file)
                log_filename = config.get('log_file_name')

        if not log_filename:
            log_filename = 'napview_log.log'

        log_path = base_path / log_filename
        existing_file_handler = next(
            (handler for handler in logger.handlers if isinstance(handler, logging.FileHandler)),
            None
        )
        if force or existing_file_handler is None or Path(existing_file_handler.baseFilename) != log_path:
            for handler in list(logger.handlers):
                if isinstance(handler, logging.FileHandler):
                    logger.removeHandler(handler)
                    handler.close()
            handler = logging.FileHandler(log_path, mode='a')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(processName)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
    except Exception as e:
        print(f"Error configuring logger: {e}")
    return logger





class ConfigManager:
    def __init__(self, base_path, load_defaults=False):
        self.logger = logging.getLogger('napview_logger')
        self.config_path = os.path.join(base_path, "config.json")
        self.config_lock = threading.RLock()  # reentrant lock
        
        if load_defaults:
            try:
                self.load_config_defaults(base_path)
                self.save_config({'base_path': str(base_path)})
            except Exception as e:
                self.logger.error(f"Error loading default config during initialization: {e}", exc_info=True)
        else:
            try:
                self.load_config()
            except Exception as e:
                self.logger.error(f"Error loading config during initialization: {e}", exc_info=True)


    def load_config_defaults(self, base_path):
        config_json_path = os.path.join(base_path, 'config.json')
        if os.path.exists(config_json_path):
            self.load_config()
            return

        config_defaults_path = str(get_resource_root() / "CONFIG_DEFAULTS.txt")
        try:
            with open(config_defaults_path, 'r') as file:
                config_defaults = json.load(file)
                with open(config_json_path, 'w') as config_file:
                    json.dump(config_defaults, config_file, indent=4)
                    self.logger.info("config.json created with default values.")
            self.load_config()

        except Exception as e:
            self.logger.error(f"Failed to create config.json: {e}", exc_info=True)
            raise(e)

    def load_config(self, instance=None):
        with self.config_lock:
            try:
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r') as config_file:
                        self.config = json.load(config_file)
                else:
                    self.config = {}
                if instance is not None:
                    for key, value in self.config.items():
                        setattr(instance, key, value)
                    setattr(instance, 'config', self.config)
            except Exception as e:
                self.logger.error(f"Error loading config: {e}", exc_info=True)
                self.config = {}
            return self.config


    def save_config(self, config_dict=None):
        with self.config_lock:
            try:
                config_to_save = {}
                if os.path.exists(self.config_path):
                    with open(self.config_path, 'r') as config_file:
                        config_to_save = json.load(config_file)
                if config_dict:
                    config_to_save.update(config_dict)
                    #self.config.update(config_dict)
                with open(self.config_path, 'w') as config_file:
                    #json.dump(self.config, config_file, indent=4)
                    json.dump(config_to_save, config_file, indent=4)
            except Exception as e:
                self.logger.error(f"Error saving config: {e}", exc_info=True)


# class ConfigManager:
#     def __init__(self, base_path, load_defaults=False):
#         # Ensure logger is configured. If called from different modules,
#         # logging.getLogger('napview_logger') should get the same logger
#         # if it was configured once (e.g., in napview_backend.py).
#         # If each ConfigManager instance needs its own logger name based on module:
#         # self.logger = logging.getLogger(f"{__name__}.ConfigManager")
#         self.logger = logging.getLogger('napview_logger') # Assuming global 'napview_logger'
        
#         self.config_path = os.path.join(base_path, "config.json")
#         self.config_lock = threading.RLock()  # Reentrant lock for thread safety within a process
#                                             # This lock does NOT synchronize file access across different processes.
        
#         # Internal attribute to hold the config, primarily for save_config to know what to merge with.
#         # load_config will primarily return data read fresh from the file.
#         self._current_config_data = {} 

#         if load_defaults:
#             try:
#                 self.logger.info(f"ConfigManager (PID {os.getpid()}): Initializing with defaults (load_defaults=True).")
#                 self.load_config_defaults(base_path) # This will load defaults and save them
#                 # After loading defaults and saving, ensure base_path is in the config
#                 # self.save_config will read, update, and write.
#                 self.save_config({'base_path': str(base_path)})
#             except Exception as e:
#                 self.logger.error(f"ConfigManager (PID {os.getpid()}): Error loading default config during initialization: {e}", exc_info=True)
#         else:
#             # If not loading defaults, attempt to load existing.
#             # The load_config method itself will handle reading from file.
#             # We can prime _current_config_data here.
#             try:
#                 self.logger.info(f"ConfigManager (PID {os.getpid()}): Initializing (load_defaults=False), attempting to load existing config.")
#                 self._current_config_data = self._read_from_file()
#                 if not self._current_config_data: # File didn't exist or was empty/invalid
#                      self.logger.warning(f"ConfigManager (PID {os.getpid()}): No existing config found or read error, may use defaults if accessed before save.")
#                      # Potentially load defaults here if _read_from_file indicates non-existence and that's desired.
#                      # For now, it means _current_config_data is {} if file is missing.
#             except Exception as e:
#                 self.logger.error(f"ConfigManager (PID {os.getpid()}): Error loading config during initialization: {e}", exc_info=True)
#                 self._current_config_data = {}


#     def _read_from_file(self):
#         """
#         Helper to read config from file. This is the ONLY place that reads the file.
#         Returns the loaded dictionary or an empty dict on error/not found.
#         """
#         # This lock primarily protects threaded access within *one* process to self.config_path.
#         # It does NOT synchronize against other processes reading/writing the same file.
#         # For inter-process file locking, more complex mechanisms like flock (POSIX) or
#         # lockfiles would be needed, but often careful sequencing is enough.
#         with self.config_lock: 
#             try:
#                 if os.path.exists(self.config_path):
#                     # Add a small delay before reading, hoping a write from another process has completed.
#                     # This is a heuristic and not a guaranteed solution for race conditions.
#                     # time.sleep(0.05) # 50ms, adjust as needed, or remove if causing too much delay.
#                     with open(self.config_path, 'r') as config_file:
#                         data = json.load(config_file)
#                         self.logger.debug(f"ConfigManager (PID {os.getpid()}): Read from {self.config_path}: {data}")
#                         return data
#                 else:
#                     self.logger.warning(f"ConfigManager (PID {os.getpid()}): Config file not found at {self.config_path} during _read_from_file.")
#                     return {}
#             except json.JSONDecodeError as e:
#                 self.logger.error(f"ConfigManager (PID {os.getpid()}): Error decoding JSON from {self.config_path}: {e}. Returning empty config.", exc_info=True)
#                 # Optionally, you could try to recover a backup or delete the corrupted file.
#                 return {}
#             except Exception as e:
#                 self.logger.error(f"ConfigManager (PID {os.getpid()}): Error reading config from {self.config_path}: {e}. Returning empty config.", exc_info=True)
#                 return {}

#     def load_config_defaults(self, base_path):
#         """
#         Replaces config.json with defaults from CONFIG_DEFAULTS.txt.
#         Also updates the internal _current_config_data.
#         """
#         with self.config_lock:
#             config_json_path = self.config_path # Use self.config_path
#             # if os.path.exists(config_json_path): # No need to remove, write will overwrite
#             #     os.remove(config_json_path)

#             # This assumes CONFIG_DEFAULTS.txt is in the same directory as the ConfigManager.py file.
#             # If ConfigManager.py is in 'napview' and CONFIG_DEFAULTS.txt is also in 'napview':
#             defaults_file_dir = os.path.dirname(os.path.abspath(__file__))
#             config_defaults_path = os.path.join(defaults_file_dir, 'CONFIG_DEFAULTS.txt')
            
#             loaded_defaults = {}
#             try:
#                 with open(config_defaults_path, 'r') as file:
#                     loaded_defaults = json.load(file)
                
#                 # Now write these defaults to the actual config.json
#                 with open(config_json_path, 'w') as config_file:
#                     json.dump(loaded_defaults, config_file, indent=4)
#                 self.logger.info(f"ConfigManager (PID {os.getpid()}): {config_json_path} created/overwritten with default values from {config_defaults_path}.")
#                 self._current_config_data = loaded_defaults.copy() # Update internal state
#             except FileNotFoundError:
#                 self.logger.error(f"ConfigManager (PID {os.getpid()}): CONFIG_DEFAULTS.txt not found at {config_defaults_path}. Cannot load defaults.")
#                 self._current_config_data = {} # Ensure internal state is empty
#                 # Write an empty config.json if defaults are missing, or raise error
#                 with open(config_json_path, 'w') as config_file:
#                     json.dump({}, config_file, indent=4)
#                 raise # Re-raise so the caller knows defaults failed
#             except Exception as e:
#                 self.logger.error(f"ConfigManager (PID {os.getpid()}): Failed to load/write defaults: {e}", exc_info=True)
#                 self._current_config_data = {}
#                 # Consider what to do if writing defaults fails.
#                 raise


#     def load_config(self, instance=None):
#         """
#         Reads configuration fresh from the file and returns it.
#         Optionally updates attributes of 'instance'.
#         Also updates the ConfigManager's internal _current_config_data for save_config's reference.
#         """
#         # _read_from_file() already handles the lock for file reading.
#         # It's important that this call is not inside the self.config_lock here if _read_from_file
#         # also takes the lock, to avoid deadlocking a RLock (though RLock allows re-entry by same thread).
#         # For clarity, ensure _read_from_file is the sole file reader.
        
#         # This method now ALWAYS reads from the file to get the freshest data.
#         config_data_from_file = self._read_from_file()
        
#         # Update the internal cache used by save_config for merging.
#         # This needs to be locked if multiple threads in the same process might call load_config and save_config concurrently.
#         with self.config_lock:
#             self._current_config_data = config_data_from_file.copy() 

#         if instance is not None:
#             self.logger.debug(f"ConfigManager (PID {os.getpid()}): Setting attributes on instance {type(instance)} from loaded config.")
#             for key, value in config_data_from_file.items():
#                 try:
#                     setattr(instance, key, value)
#                 except Exception as e:
#                     self.logger.warning(f"ConfigManager (PID {os.getpid()}): Failed to set attribute '{key}' on instance: {e}")
#             try: # Also set the 'config' attribute on the instance to this fresh data
#                 setattr(instance, 'config', config_data_from_file.copy())
#             except Exception as e:
#                 self.logger.warning(f"ConfigManager (PID {os.getpid()}): Failed to set attribute 'config' on instance: {e}")

#         # Return a copy of the data read from the file.
#         return config_data_from_file.copy()


#     def save_config(self, config_dict_to_merge=None):
#         """
#         Merges config_dict_to_merge with the current internal configuration data,
#         then writes the result to the config file.
#         """
#         with self.config_lock: # Protects access to self._current_config_data and file writing
#             try:
#                 # If _current_config_data is empty (e.g. first run, or read failed),
#                 # it's better to re-read before merging, or ensure it's appropriately primed.
#                 # However, load_config is now designed to be called first by users.
#                 # For safety, if _current_config_data seems uninitialized, one might re-read.
#                 # But this could lead to overwriting if not careful.
#                 # The current design expects _current_config_data to be the "last known good" or "last loaded" state.

#                 if config_dict_to_merge:
#                     self.logger.debug(f"ConfigManager (PID {os.getpid()}): Merging into config: {config_dict_to_merge}")
#                     self._current_config_data.update(config_dict_to_merge)
                
#                 # Write the (potentially updated) _current_config_data to disk
#                 with open(self.config_path, 'w') as config_file:
#                     json.dump(self._current_config_data, config_file, indent=4)
#                 self.logger.info(f"ConfigManager (PID {os.getpid()}): Config saved to {self.config_path} with content: {self._current_config_data}")
#             except Exception as e:
#                 self.logger.error(f"ConfigManager (PID {os.getpid()}): Error saving config to {self.config_path}: {e}", exc_info=True)
