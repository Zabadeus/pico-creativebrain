"""
Shared enums for PICO application.
"""
from enum import Enum

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

class InputType(Enum):
    """Types of input sources."""
    LOCAL_FILE = "local_file"
    YOUTUBE = "youtube"
    PODCAST = "podcast"
    LIVE_RECORDING = "live_recording"
    WEB_AUDIO = "web_audio"

class ExportFormat(Enum):
    """Supported export formats."""
    TXT = "txt"
    SRT = "srt"
    VTT = "vtt"
    JSON = "json"
    ZIP = "zip"
    HTML = "html"
    MARKDOWN = "markdown"