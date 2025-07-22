"""
Audio utilities for PICO application.
"""
import librosa
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

def get_audio_duration(file_path: str) -> float:
    """Get audio duration in seconds."""
    try:
        duration = librosa.get_duration(filename=file_path)
        return float(duration)
    except Exception as e:
        logger.error(f"Error getting audio duration for {file_path}: {e}")
        return 0.0

def get_audio_sample_rate(file_path: str) -> int:
    """Get audio sample rate."""
    try:
        return librosa.get_samplerate(file_path)
    except Exception as e:
        logger.error(f"Error getting sample rate for {file_path}: {e}")
        return 0

def validate_audio_file(file_path: str) -> bool:
    """Validate if file is a supported audio format."""
    supported_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.wma', '.aac'}
    return Path(file_path).suffix.lower() in supported_extensions

def convert_timestamp_to_string(seconds: float) -> str:
    """Convert seconds to HH:MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}"

def convert_timestamp_to_hms(seconds: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')

def normalize_audio_path(file_path: str) -> str:
    """Normalize audio file path."""
    return str(Path(file_path).resolve())