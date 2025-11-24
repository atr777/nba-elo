"""
File I/O utilities for the NBA ELO Intelligence Engine.
Handles reading/writing CSV, YAML, and other data formats.
"""

import os
import csv
import yaml
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_yaml(filepath: str) -> Dict[str, Any]:
    """Load YAML configuration file."""
    with open(filepath, 'r') as f:
        return yaml.safe_load(f)


def save_yaml(data: Dict[str, Any], filepath: str) -> None:
    """Save dictionary to YAML file."""
    with open(filepath, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)


def load_csv_to_dataframe(filepath: str) -> pd.DataFrame:
    """Load CSV file into pandas DataFrame."""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"CSV file not found: {filepath}")
    return pd.read_csv(filepath)


def save_dataframe_to_csv(df: pd.DataFrame, filepath: str, index: bool = False) -> None:
    """Save pandas DataFrame to CSV file."""
    # Ensure directory exists
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    df.to_csv(filepath, index=index)
    print(f"[OK] Saved: {filepath} ({len(df)} rows)")


def ensure_directory(directory: str) -> None:
    """Create directory if it doesn't exist."""
    Path(directory).mkdir(parents=True, exist_ok=True)


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_config_path(filename: str) -> str:
    """Get full path to config file."""
    return str(get_project_root() / "config" / filename)


def get_data_path(subdir: str, filename: str) -> str:
    """Get full path to data file in specified subdirectory."""
    return str(get_project_root() / "data" / subdir / filename)


def load_settings() -> Dict[str, Any]:
    """Load main settings configuration."""
    return load_yaml(get_config_path("settings.yaml"))


def load_constants() -> Dict[str, Any]:
    """Load constants configuration."""
    return load_yaml(get_config_path("constants.yaml"))
