from flask import Flask, render_template, jsonify, request
import os
import json
import webbrowser
import logging
from threading import Timer

from .helpers import configure_logger, ConfigManager, get_resource_root
from .database_handler import DatabaseHandler

class Visualizer:
    
    STAGING_DESIRED_FIELDS = ['w', 'n1', 'n2', 'n3', 'rem']
    YASA_DESIRED_FIELDS = ['alpha_power', 'beta_power', 'theta_power', 'delta_power', 'gamma_power']

    def __init__(self, base_path, mode):
        self.base_path = base_path
        resource_root = get_resource_root()
        template_folder = str(resource_root / "templates")
        static_folder = str(resource_root / "static")
        self.app = Flask(__name__, template_folder=template_folder, static_folder=static_folder)
        log = logging.getLogger('werkzeug')
        log.setLevel(logging.ERROR)
        log.disabled = True
        self.setup_routes()

        # setup logging
        self.logger = configure_logger(self.base_path)
        self.logger.info('Visualizer: started...')

        # load variables from config.json
        self.config_manager = ConfigManager(self.base_path)
        self.config = self.config_manager.load_config(instance=self)

        self.db_handler = DatabaseHandler(self.base_path)
        self.db_handler.setup_database()

        self.visualizer_port = self.config.get('visualizer_port', 8080)

    def setup_routes(self):
        @self.app.route('/')
        def home():
            try:
                return render_template('index.html')
            except Exception as e:
                self.logger.error(f"Error rendering template 'index.html': {e}", exc_info=True)
                return "An error occurred", 500

        @self.app.route('/load_config')
        def load_config():
            try:
                self.config = self.config_manager.load_config(instance=self)
                return jsonify(self.config)
            except Exception as e:
                self.logger.error(f"Error in /load_config endpoint: {e}", exc_info=True)
                return jsonify({'error': 'An error occurred'}), 500

        @self.app.route('/update_config', methods=['POST'])
        def update_config():
            try:
                config_updates = request.get_json()
                self.config_manager.save_config(config_updates)
                return jsonify({'status': 'Configuration updated'})
            except Exception as e:
                self.logger.error(f"Error in /update_config endpoint: {e}", exc_info=True)
                return jsonify({'error': 'An error occurred'}), 500

        @self.app.route('/data1')
        def data1():
            try:
                data = self.db_handler.get_all_analysis_results(self.STAGING_DESIRED_FIELDS)
                return jsonify(data)
            except Exception as e:
                self.logger.error(f"Error in /data1 endpoint: {e}", exc_info=True)
                return jsonify({'error': 'An error occurred'}), 500

        @self.app.route('/data2')
        def data2():
            try:
                data = self.db_handler.get_all_analysis_results(self.YASA_DESIRED_FIELDS)
                return jsonify(data)
            except Exception as e:
                self.logger.error(f"Error in /data2 endpoint: {e}", exc_info=True)
                return jsonify({'error': 'An error occurred'}), 500

    def run(self):
        try:

            def open_browser():
                webbrowser.open(f"http://127.0.0.1:{self.visualizer_port}", new=2)
            Timer(1, open_browser).start()
            self.app.run(debug=False, port=self.visualizer_port)

        except Exception as e:
            self.logger.error(f"Error running the Visualizer: {e}", exc_info=True)

    def shutdown(self):
        pass


class DataLoader:
    def __init__(self, data_file, desired_fields, base_path):
        self.data_file = str(get_resource_root() / data_file)
        self.desired_fields = desired_fields
        self.logger = configure_logger(base_path)

    def load_data(self):
        data = {}
        try:
            with open(self.data_file, 'r') as file:
                for line in file:
                    entry = json.loads(line)
                    x = entry['start_time']
                    for field, value in entry.items():
                        if field in self.desired_fields:
                            if field not in data:
                                data[field] = []
                            data[field].append({'x': x, 'y': value})
        except Exception as e:
            #self.logger.error(f"Error loading data from {self.data_file}: {e}", exc_info=True)
            # File does not exist, generate one minute of null data
            for field in self.desired_fields:
                data[field] = [{'x': x, 'y': 0} for x in range(0, 60)]
        return data
