"""
Centralized configuration for PICO application.
"""
import os
from dataclasses import dataclass
from typing import Optional

@dataclass
class AppConfig:
    """Application configuration."""
    # Base paths
    BASE_PATH: str = os.getenv("PICO_BASE_PATH", "transcripts")
    TEMP_DIR: str = os.getenv("PICO_TEMP_DIR", "temp")
    MODELS_DIR: str = os.getenv("PICO_MODELS_DIR", "models")
    
    # Transcription settings
    DEFAULT_MODEL_SIZE: str = os.getenv("PICO_MODEL_SIZE", "base")
    DEFAULT_DEVICE: str = os.getenv("PICO_DEVICE", "auto")
    DEFAULT_COMPUTE_TYPE: str = os.getenv("PICO_COMPUTE_TYPE", "auto")
    
    # Audio settings
    SAMPLE_RATE: int = int(os.getenv("PICO_SAMPLE_RATE", "16000"))
    CHUNK_SIZE: int = int(os.getenv("PICO_CHUNK_SIZE", "512"))
    
    # Privacy settings
    DEFAULT_PRIVACY_MODE: str = os.getenv("PICO_PRIVACY_MODE", "full")
    
    # Server settings
    API_HOST: str = os.getenv("PICO_API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("PICO_API_PORT", "8000"))
    
    # Feature flags
    ENABLE_DIARIZATION: bool = os.getenv("PICO_ENABLE_DIARIZATION", "true").lower() == "true"
    ENABLE_CLOUD_SYNC: bool = os.getenv("PICO_ENABLE_CLOUD_SYNC", "false").lower() == "true"
    
    # Database settings
    DATABASE_PATH: str = os.getenv("PICO_DATABASE_PATH", "pico_index.db")
    
    @classmethod
    def from_env(cls) -> 'AppConfig':
        """Create config from environment variables."""
        return cls()

# Global config instance
config = AppConfig.from_env()