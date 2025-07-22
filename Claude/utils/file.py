"""
File utilities for PICO application.
"""
import os
from pathlib import Path
from typing import Optional

def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if it doesn't."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path

def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(file_path)
    except (OSError, FileNotFoundError):
        return 0

def file_exists(file_path: str) -> bool:
    """Check if file exists."""
    return os.path.exists(file_path) and os.path.isfile(file_path)

def directory_exists(dir_path: str) -> bool:
    """Check if directory exists."""
    return os.path.exists(dir_path) and os.path.isdir(dir_path)

def get_file_extension(file_path: str) -> str:
    """Get file extension."""
    return Path(file_path).suffix.lower()

def generate_unique_filename(base_path: str, filename: str, extension: str) -> str:
    """Generate a unique filename by adding a number suffix if needed."""
    base_name = filename
    counter = 1
    full_path = os.path.join(base_path, f"{base_name}{extension}")
    
    while os.path.exists(full_path):
        full_path = os.path.join(base_path, f"{base_name}_{counter}{extension}")
        counter += 1
        
    return full_path

def get_directory_size(directory: str) -> int:
    """Calculate total size of directory in bytes."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, FileNotFoundError):
                pass
    return total_size