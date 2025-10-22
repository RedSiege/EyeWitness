#!/usr/bin/env python3
"""
Configuration file support for EyeWitness
Allows loading settings from config files
"""

import os
import json
import configparser
from pathlib import Path


class ConfigManager:
    """Manage EyeWitness configuration files"""
    
    DEFAULT_CONFIG_LOCATIONS = [
        Path.home() / '.eyewitness' / 'config.json',
        Path.home() / '.config' / 'eyewitness' / 'config.json',
        Path('.eyewitness.json'),
        Path('eyewitness.json'),
    ]
    
    DEFAULT_CONFIG = {
        'threads': None,  # Will use CPU-based calculation
        'timeout': 7,
        'delay': 0,
        'jitter': 0,
        'user_agent': None,
        'proxy_ip': None,
        'proxy_port': None,
        'output_dir': './sessions',
        'prepend_https': False,
        'show_selenium': False,
        'resolve': False,
        'skip_validation': False,
        'results_per_page': 25,
        'max_retries': 1
    }
    
    @staticmethod
    def find_config_file(config_path=None):
        """
        Find configuration file
        
        Args:
            config_path (str): Explicit config file path
            
        Returns:
            Path or None
        """
        if config_path:
            path = Path(config_path)
            if path.exists():
                return path
            else:
                print(f"[!] Config file not found: {config_path}")
                return None
        
        # Check default locations
        for location in ConfigManager.DEFAULT_CONFIG_LOCATIONS:
            if location.exists():
                return location
        
        return None
    
    @staticmethod
    def load_config(config_path=None):
        """
        Load configuration from file
        
        Args:
            config_path (str): Path to config file
            
        Returns:
            dict: Configuration dictionary
        """
        config_file = ConfigManager.find_config_file(config_path)
        
        if not config_file:
            return {}
        
        try:
            print(f"[*] Loading config from: {config_file}")
            
            if config_file.suffix == '.json':
                with open(config_file, 'r') as f:
                    config = json.load(f)
            elif config_file.suffix in ['.ini', '.conf']:
                config = ConfigManager._load_ini_config(config_file)
            else:
                print(f"[!] Unsupported config format: {config_file.suffix}")
                return {}
            
            # Validate config
            validated = ConfigManager._validate_config(config)
            return validated
            
        except Exception as e:
            print(f"[!] Error loading config: {e}")
            return {}
    
    @staticmethod
    def _load_ini_config(config_file):
        """Load INI-style config file"""
        parser = configparser.ConfigParser()
        parser.read(config_file)
        
        config = {}
        
        # Map INI sections to flat config
        if 'general' in parser:
            for key, value in parser['general'].items():
                # Convert string values to appropriate types
                if value.lower() in ['true', 'false']:
                    config[key] = value.lower() == 'true'
                elif value.isdigit():
                    config[key] = int(value)
                else:
                    config[key] = value
        
        if 'network' in parser:
            if 'proxy_ip' in parser['network']:
                config['proxy_ip'] = parser['network']['proxy_ip']
            if 'proxy_port' in parser['network']:
                config['proxy_port'] = int(parser['network']['proxy_port'])
        
        return config
    
    @staticmethod
    def _validate_config(config):
        """Validate and clean configuration"""
        validated = {}
        
        # Integer fields
        int_fields = ['threads', 'timeout', 'delay', 'jitter', 'proxy_port', 
                     'results_per_page', 'max_retries']
        for field in int_fields:
            if field in config:
                try:
                    validated[field] = int(config[field])
                except (ValueError, TypeError):
                    print(f"[!] Invalid {field} value in config: {config[field]}")
        
        # Boolean fields
        bool_fields = ['prepend_https', 'show_selenium', 'resolve', 'skip_validation']
        for field in bool_fields:
            if field in config:
                validated[field] = bool(config[field])
        
        # String fields
        str_fields = ['user_agent', 'proxy_ip', 'output_dir']
        for field in str_fields:
            if field in config and config[field]:
                validated[field] = str(config[field])
        
        return validated
    
    @staticmethod
    def apply_config_to_args(args, config):
        """
        Apply configuration to argparse args
        
        Args:
            args: Argparse namespace
            config (dict): Configuration dictionary
            
        Returns:
            args: Modified args with config applied
        """
        if not config:
            return args
        
        # Only apply config values that weren't explicitly set on command line
        for key, value in config.items():
            if hasattr(args, key):
                # Check if this was a default value
                if key == 'threads' and args.threads == 10 and value:
                    # Default threads is 10, so override with config
                    args.threads = value
                elif key == 'timeout' and args.timeout == 7 and value:
                    args.timeout = value
                elif key == 'output_dir' and args.d == './sessions' and value:
                    args.d = value
                elif key == 'results_per_page' and args.results == 25 and value:
                    args.results = value
                # For boolean flags, only apply if not already set
                elif key in ['prepend_https', 'show_selenium', 'resolve', 'skip_validation']:
                    if not getattr(args, key, False) and value:
                        setattr(args, key, value)
                # For other fields, apply if current value is None/default
                elif getattr(args, key, None) is None and value is not None:
                    setattr(args, key, value)
        
        return args
    
    @staticmethod
    def create_sample_config(output_path=None):
        """Create a sample configuration file"""
        if not output_path:
            output_path = Path.home() / '.eyewitness' / 'config.json.sample'
        
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        sample_config = {
            "_comment": "EyeWitness configuration file",
            "threads": 10,
            "timeout": 30,
            "delay": 0,
            "jitter": 0,
            "user_agent": None,
            "proxy_ip": None,
            "proxy_port": None,
            "output_dir": "./sessions",
            "prepend_https": False,
            "show_selenium": False,
            "resolve": False,
            "skip_validation": False,
            "results_per_page": 25,
            "max_retries": 2
        }
        
        with open(output_path, 'w') as f:
            json.dump(sample_config, f, indent=4)
        
        print(f"[*] Sample config written to: {output_path}")
        return output_path