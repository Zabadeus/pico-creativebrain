"""
Centralized data models for the PICO application.
Contains all Enums and Dataclasses used across different services.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any


class StorageError(Exception):
    """Custom exception for storage-related errors"""
    pass


# --- Enums ---

class VersionType(Enum):
    """Supported content version types"""
    ORIGINAL = "original"
    CLEANED = "cleaned"
    SUMMARY_BRIEF = "summary_brief"
    SUMMARY_DETAILED = "summary_detailed"
    SUMMARY_KEYPOINTS = "summary_keypoints"


class CleaningLevel(Enum):
    """Different levels of content cleaning"""
    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"


class PrivacyMode(Enum):
    """Privacy modes for content handling"""
    PRIVATE = "private"  # No AI processing, local only
    SELECTIVE = "selective"  # User controls what goes to AI
    OPEN = "open"  # All content can be processed by AI


class DataSensitivity(Enum):
    """Data sensitivity levels for GDPR/CCPA compliance"""
    PUBLIC = "public"
    PERSONAL = "personal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class AIProvider(Enum):
    """Supported AI providers"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    GOOGLE = "google"
    HUGGINGFACE = "huggingface"
    OPENROUTER = "openrouter"
    LOCAL = "local"


# --- Dataclasses ---

@dataclass
class TimestampedSegment:
    """Represents a timestamped text segment"""
    start_time: float
    end_time: float
    text: str
    speaker: Optional[str] = None
    confidence: Optional[float] = None
    version_metadata: Optional[Dict[str, Any]] = None


@dataclass
class ContentVersion:
    """Container for a specific version of content"""
    version_type: VersionType
    segments: List[TimestampedSegment]
    full_text: str
    metadata: Dict[str, Any]
    created_at: datetime
    word_count: int
    processing_time: Optional[float] = None


@dataclass
class TranscriptionSegment:
    """Represents a single transcription segment with timing and metadata."""
    id: int
    text: str
    start: float
    end: float
    confidence: float
    speaker: Optional[str] = None
    words: Optional[List[Dict]] = None


@dataclass
class TranscriptionResult:
    """Complete transcription result with metadata."""
    segments: List[TranscriptionSegment]
    language: str
    duration: float
    processing_time: float
    model_used: str
    source_info: Dict
    speaker_count: Optional[int] = None


@dataclass
class SessionMetadata:
    """Session metadata structure"""
    session_id: str
    created: str  # ISO format datetime
    updated: str  # ISO format datetime
    duration: str  # HH:MM:SS format
    speaker_count: int
    privacy_mode: str
    ai_processed: bool
    source_file: Optional[str] = None
    file_size: Optional[int] = None
    sample_rate: Optional[int] = None
    channels: Optional[int] = None
    language: Optional[str] = None
    processing_settings: Optional[Dict[str, Any]] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None


@dataclass
class KnowledgeData:
    """Knowledge management data structure"""
    tags: List[str]
    auto_tags: List[str]
    manual_tags: List[str]
    links: Dict[str, List[str]]  # session_id -> list of linked sessions
    insights: List[str]
    key_points: List[str]
    topics: List[str]
    created: str
    updated: str


@dataclass
class AIUsageLog:
    """Log for tracking AI provider usage for transparency and compliance."""
    content_hash: str
    provider: AIProvider
    task_type: str
    timestamp: datetime
    data_sent_size: int
    anonymized: bool
    user_approved: bool
    retention_days: int


@dataclass
class PrivacySettings:
    """Stores user-configurable privacy settings."""
    mode: PrivacyMode
    allowed_providers: List[AIProvider]
    auto_anonymize: bool
    require_approval: bool
    max_retention_days: int
    sensitive_patterns: List[str]
    blocked_content_types: List[str]