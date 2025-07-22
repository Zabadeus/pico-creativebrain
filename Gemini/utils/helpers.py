"""
Utility functions for the PICO application.
"""

from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse


def generate_session_id() -> str:
    """Generate a unique session ID based on the current timestamp."""
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def format_duration_from_seconds(total_seconds: float) -> str:
    """Format duration from seconds to HH:MM:SS."""
    hours = int(total_seconds // 3600)
    minutes = int((total_seconds % 3600) // 60)
    seconds = int(total_seconds % 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def seconds_to_srt_time(seconds: float) -> str:
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def seconds_to_vtt_time(seconds: float) -> str:
    """Convert seconds to WebVTT time format (HH:MM:SS.mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"


def get_directory_size(path: Path) -> int:
    """Calculate total size of a directory."""
    total_size = 0
    for file_path in path.rglob('*'):
        if file_path.is_file():
            total_size += file_path.stat().st_size
    return total_size


def format_file_size(size_bytes: int) -> str:
    """Format file size in a human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"


def is_url(source: str) -> bool:
    """Check if the source string is a URL."""
    parsed = urlparse(source)
    return bool(parsed.scheme and parsed.netloc)


def is_rss_feed(url: str) -> bool:
    """Check if a URL is likely an RSS feed by attempting to parse it."""
    try:
        import feedparser
        feed = feedparser.parse(url)
        return bool(feed.entries)
    except (ImportError, Exception):
        return False