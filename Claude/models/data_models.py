"""
Shared data models for PICO application.
"""
from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import json

class VersionType(Enum):
    """Types of content versions."""
    ORIGINAL = "original"
    CLEANED = "cleaned"
    SUMMARY_BRIEF = "summary_brief"
    SUMMARY_DETAILED = "summary_detailed"
    SUMMARY_KEYPOINTS = "summary_keypoints"

class PrivacyMode(Enum):
    """Privacy modes for content handling."""
    FULL = "full"
    SELECTIVE = "selective"
    METADATA_ONLY = "metadata_only"
    NONE = "none"

@dataclass
class TimestampedSegment:
    """Represents a segment of content with timestamps."""
    start_time: float
    end_time: float
    text: str
    speaker: Optional[str] = None
    confidence: float = 1.0

@dataclass
class ContentVersion:
    """Represents a version of content."""
    version_type: VersionType
    segments: List[TimestampedSegment]
    full_text: str
    metadata: Dict[str, Any]
    created_at: datetime
    word_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        data = asdict(self)
        data['version_type'] = self.version_type.value
        data['created_at'] = self.created_at.isoformat()
        data['segments'] = [
            {
                'start_time': seg.start_time,
                'end_time': seg.end_time,
                'text': seg.text,
                'speaker': seg.speaker,
                'confidence': seg.confidence
            }
            for seg in self.segments
        ]
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ContentVersion':
        """Create from dictionary."""
        segments = [
            TimestampedSegment(
                start_time=seg['start_time'],
                end_time=seg['end_time'],
                text=seg['text'],
                speaker=seg.get('speaker'),
                confidence=seg.get('confidence', 1.0)
            )
            for seg in data['segments']
        ]
        
        return cls(
            version_type=VersionType(data['version_type']),
            segments=segments,
            full_text=data['full_text'],
            metadata=data['metadata'],
            created_at=datetime.fromisoformat(data['created_at']),
            word_count=data.get('word_count', 0)
        )

@dataclass
class SessionMetadata:
    """Session metadata structure."""
    session_id: str
    created: str
    updated: str
    duration: str
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
    """Knowledge management data structure."""
    tags: List[str]
    auto_tags: List[str]
    manual_tags: List[str]
    links: Dict[str, List[str]]
    insights: List[str]
    key_points: List[str]
    topics: List[str]
    created: str
    updated: str

@dataclass
class InputResult:
    """Result of input processing."""
    success: bool
    audio_path: Optional[str] = None
    title: Optional[str] = None
    duration: Optional[float] = None
    source_type: Optional[str] = None
    source_url: Optional[str] = None
    error: Optional[str] = None