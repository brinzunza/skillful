"""
Configuration management for Skillful agent.
"""

import os
import yaml
from typing import Dict, Any
from pathlib import Path


DEFAULT_CONFIG = {
    "model": "gpt-4o-mini",
    "max_iterations": 20,
    "temperature": 0.7,
    "safety": {
        "enabled": True,
        "max_high_risk_operations": 10,
        "require_confirmation": ["delete_file"]
    },
    "memory": {
        "enabled": True,
        "auto_save": True
    },
    "async": {
        "enabled": False,
        "max_concurrent_tasks": 1
    },
    "undo": {
        "enabled": True,
        "use_git": True,
        "auto_commit": True
    }
}

CONFIG_FILE = ".skillful/config.yaml"


class Config:
    """Manages configuration for Skillful agent."""

    def __init__(self, config_path: str = CONFIG_FILE):
        """
        Initialize configuration.

        Args:
            config_path: Path to config file
        """
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or create default."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    user_config = yaml.safe_load(f) or {}
                    # Merge with defaults
                    return self._merge_configs(DEFAULT_CONFIG.copy(), user_config)
            except (yaml.YAMLError, IOError) as e:
                print(f"Warning: Could not load config: {e}")
                return DEFAULT_CONFIG.copy()
        else:
            # Create default config file
            self._save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG.copy()

    def _merge_configs(self, base: Dict, override: Dict) -> Dict:
        """
        Recursively merge two config dictionaries.

        Args:
            base: Base configuration
            override: Override configuration

        Returns:
            Merged configuration
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def _save_config(self, config: Dict):
        """Save configuration to file."""
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)

        try:
            with open(self.config_path, 'w') as f:
                yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
        except IOError as e:
            print(f"Warning: Could not save config: {e}")

    def get(self, key: str, default=None) -> Any:
        """
        Get configuration value.

        Args:
            key: Configuration key (supports dot notation, e.g., "safety.enabled")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        Set configuration value.

        Args:
            key: Configuration key (supports dot notation)
            value: Value to set
        """
        keys = key.split('.')
        config = self.config

        # Navigate to the nested key
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # Set the value
        config[keys[-1]] = value

        # Save to file
        self._save_config(self.config)

    def reload(self):
        """Reload configuration from file."""
        self.config = self._load_config()

    def reset_to_defaults(self):
        """Reset configuration to defaults."""
        self.config = DEFAULT_CONFIG.copy()
        self._save_config(self.config)

    def get_all(self) -> Dict[str, Any]:
        """Get entire configuration."""
        return self.config.copy()
