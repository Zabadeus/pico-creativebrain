"""
Version management service for PICO application.
"""
import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

from core.exceptions import StorageError
from core.events import event_bus, Event, EventType
from models.data_models import ContentVersion, VersionType, TimestampedSegment
from utils.file import ensure_directory
from utils.logger import get_logger

logger = get_logger(__name__)

class VersionManager:
    """
    Manages content versions (original, cleaned, summary) for transcription sessions.
    """
    
    def __init__(self, base_path: str = "transcripts"):
        """
        Initialize the version manager.
        
        Args:
            base_path: Root directory for all transcript storage
        """
        self.base_path = Path(base_path)
        self.version_files = {
            VersionType.ORIGINAL: 'versions/original.md',
            VersionType.CLEANED: 'versions/cleaned.md',
            VersionType.SUMMARY_BRIEF: 'versions/summary.md',
            VersionType.SUMMARY_DETAILED: 'versions/summary_detailed.md',
            VersionType.SUMMARY_KEYPOINTS: 'versions/keypoints.md'
        }
        
        logger.info(f"VersionManager initialized with base path: {self.base_path}")
    
    def save_version(self, session_id: str, version: ContentVersion) -> None:
        """
        Save a content version to markdown file with metadata header.
        
        Args:
            session_id: Session identifier
            version: ContentVersion to save
        """
        session_path = self._get_session_path(session_id)
        version_file = session_path / self.version_files[version.version_type]
        
        # Ensure versions directory exists
        version_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create markdown content with metadata header
        markdown_content = self._create_markdown_with_metadata(version, session_id)
        
        try:
            with open(version_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
            
            # Update session timestamp
            self._update_session_timestamp(session_id)
            
            # Publish event
            event_bus.publish(Event(
                type=EventType.VERSION_CREATED,
                data={
                    "session_id": session_id,
                    "version_type": version.version_type.value,
                    "word_count": version.word_count
                },
                timestamp=datetime.now().timestamp()
            ))
            
            logger.debug(f"Version {version.version_type.value} saved for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save version {version.version_type.value} for session {session_id}: {str(e)}")
            raise StorageError(f"Failed to save version {version.version_type.value} for session {session_id}: {str(e)}")
    
    def load_version(self, session_id: str, version_type: VersionType) -> Optional[ContentVersion]:
        """
        Load a content version from markdown file.
        
        Args:
            session_id: Session identifier
            version_type: Type of version to load
            
        Returns:
            ContentVersion or None if not found
        """
        session_path = self._get_session_path(session_id)
        version_file = session_path / self.version_files[version_type]
        
        if not version_file.exists():
            return None
        
        try:
            with open(version_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return self._parse_markdown_content(content, version_type, session_id)
            
        except Exception as e:
            logger.error(f"Failed to load version {version_type.value} for session {session_id}: {str(e)}")
            raise StorageError(f"Failed to load version {version_type.value} for session {session_id}: {str(e)}")
    
    def get_available_versions(self, session_id: str) -> List[VersionType]:
        """
        Get list of available versions for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of available version types
        """
        session_path = self._get_session_path(session_id)
        available_versions = []
        
        for version_type, file_path in self.version_files.items():
            if (session_path / file_path).exists():
                available_versions.append(version_type)
        
        return available_versions
    
    def delete_version(self, session_id: str, version_type: VersionType) -> None:
        """
        Delete a specific version.
        
        Args:
            session_id: Session identifier
            version_type: Type of version to delete
        """
        session_path = self._get_session_path(session_id)
        version_file = session_path / self.version_files[version_type]
        
        if version_file.exists():
            try:
                os.remove(version_file)
                logger.info(f"Version {version_type.value} deleted for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to delete version {version_type.value} for session {session_id}: {str(e)}")
                raise StorageError(f"Failed to delete version {version_type.value} for session {session_id}: {str(e)}")
    
    def export_version(self, session_id: str, version_type: VersionType, format: str) -> str:
        """
        Export a version in specified format.
        
        Args:
            session_id: Session identifier
            version_type: Type of version to export
            format: Export format ('txt', 'srt', 'vtt', 'json')
            
        Returns:
            Path to exported file
        """
        version = self.load_version(session_id, version_type)
        if not version:
            raise StorageError(f"Version {version_type.value} not found for session {session_id}")
        
        session_path = self._get_session_path(session_id)
        exports_dir = session_path / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = exports_dir / f"{version_type.value}_{timestamp}.{format}"
        
        try:
            if format.lower() == "txt":
                self._export_as_txt(version, export_file)
            elif format.lower() == "srt":
                self._export_as_srt(version, export_file)
            elif format.lower() == "vtt":
                self._export_as_vtt(version, export_file)
            elif format.lower() == "json":
                self._export_as_json(version, export_file)
            else:
                raise ValueError(f"Unsupported export format: {format}")
            
            logger.debug(f"Version {version_type.value} exported to {export_file}")
            return str(export_file)
            
        except Exception as e:
            logger.error(f"Failed to export version {version_type.value} for session {session_id}: {str(e)}")
            raise StorageError(f"Failed to export version {version_type.value} for session {session_id}: {str(e)}")
    
    # Private helper methods
    
    def _get_session_path(self, session_id: str) -> Path:
        """Get path to session directory."""
        return self.base_path / session_id
    
    def _update_session_timestamp(self, session_id: str) -> None:
        """Update the updated timestamp in session metadata."""
        # This would typically call into FileManager, but we'll keep it simple for now
        pass
    
    def _create_markdown_with_metadata(self, version: ContentVersion, session_id: str) -> str:
        """Create markdown content with metadata header."""
        # Create metadata header
        metadata_lines = [
            "---",
            f"version_type: {version.version_type.value}",
            f"created_at: {version.created_at.isoformat()}",
            f"word_count: {version.word_count}",
            f"session_id: {session_id}"
        ]
        
        # Add processing settings if available
        if version.metadata:
            for key, value in version.metadata.items():
                metadata_lines.append(f"{key}: {value}")
        
        metadata_lines.append("---")
        metadata_header = "\n".join(metadata_lines) + "\n\n"
        
        # Create content
        content_lines = []
        
        # Add full text if available
        if version.full_text.strip():
            content_lines.append(version.full_text)
            content_lines.append("")  # Add blank line
        
        # Add segments with timestamps
        if version.segments:
            content_lines.append("## Segments")
            content_lines.append("")
            
            for i, segment in enumerate(version.segments):
                speaker_prefix = f"[{segment.speaker}] " if segment.speaker else ""
                content_lines.append(f"{i+1}. {speaker_prefix}{segment.text}")
                content_lines.append(f"   - Time: {self._format_timestamp(segment.start_time)} - {self._format_timestamp(segment.end_time)}")
                content_lines.append(f"   - Confidence: {segment.confidence:.3f}")
                content_lines.append("")
        
        content = "\n".join(content_lines)
        
        return metadata_header + content
    
    def _parse_markdown_content(self, content: str, version_type: VersionType, session_id: str) -> ContentVersion:
        """Parse markdown content back into ContentVersion."""
        # Extract metadata header (between --- lines)
        metadata = {}
        full_text = ""
        segments = []
        
        lines = content.split('\n')
        in_metadata = False
        metadata_lines = []
        content_lines = []
        
        for line in lines:
            if line.strip() == "---":
                if not in_metadata:
                    in_metadata = True
                else:
                    in_metadata = False
                    continue
            elif in_metadata:
                metadata_lines.append(line)
            else:
                content_lines.append(line)
        
        # Parse metadata
        for line in metadata_lines:
            if ":" in line:
                key, value = line.split(":", 1)
                key = key.strip()
                value = value.strip()
                
                # Parse known fields
                if key == "created_at":
                    try:
                        created_at = datetime.fromisoformat(value)
                    except:
                        created_at = datetime.now()
                elif key == "word_count":
                    try:
                        word_count = int(value)
                    except:
                        word_count = 0
                else:
                    metadata[key] = value
        
        # Use defaults if not found
        if 'created_at' not in locals():
            created_at = datetime.now()
        if 'word_count' not in locals():
            word_count = 0
        
        # Extract full text and segments
        content_text = "\n".join(content_lines)
        
        # Look for segments section
        if "## Segments" in content_text:
            parts = content_text.split("## Segments", 1)
            full_text = parts[0].strip()
            
            # Parse segments
            segment_lines = parts[1].strip().split('\n')
            current_segment = None
            
            for line in segment_lines:
                line = line.strip()
                if line.startswith("- Time:"):
                    if current_segment:
                        # Extract time range
                        time_part = line.replace("- Time:", "").strip()
                        if " - " in time_part:
                            start_str, end_str = time_part.split(" - ", 1)
                            current_segment.start_time = self._parse_timestamp(start_str)
                            current_segment.end_time = self._parse_timestamp(end_str)
                elif line.startswith("- Confidence:"):
                    if current_segment:
                        try:
                            confidence_str = line.replace("- Confidence:", "").strip()
                            current_segment.confidence = float(confidence_str)
                        except:
                            current_segment.confidence = 1.0
                elif line and not line.startswith("##") and not line.startswith("- "):
                    if line[0].isdigit() and ". " in line:
                        # New segment
                        segment_text = line.split(". ", 1)[1]
                        speaker = None
                        text = segment_text
                        
                        # Extract speaker if present
                        if segment_text.startswith("[") and "]" in segment_text:
                            speaker_end = segment_text.find("]")
                            speaker = segment_text[1:speaker_end]
                            text = segment_text[speaker_end+2:].strip()
                        
                        current_segment = TimestampedSegment(
                            start_time=0,
                            end_time=0,
                            text=text,
                            speaker=speaker,
                            confidence=1.0
                        )
                        segments.append(current_segment)
        
        # If no segments found, create one from full text
        if not segments and full_text:
            segments.append(TimestampedSegment(
                start_time=0,
                end_time=0,
                text=full_text,
                speaker=None,
                confidence=1.0
            ))
        
        return ContentVersion(
            version_type=version_type,
            segments=segments,
            full_text=full_text,
            metadata=metadata,
            created_at=created_at,
            word_count=word_count
        )
    
    def _export_as_txt(self, version: ContentVersion, output_path: Path) -> None:
        """Export version as plain text."""
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(version.full_text)
    
    def _export_as_srt(self, version: ContentVersion, output_path: Path) -> None:
        """Export version as SRT subtitle file."""
        def format_timestamp(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(version.segments, 1):
                start_time = format_timestamp(segment.start_time)
                end_time = format_timestamp(segment.end_time)
                
                speaker_prefix = f"[{segment.speaker}] " if segment.speaker else ""
                text = f"{speaker_prefix}{segment.text}"
                
                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
    
    def _export_as_vtt(self, version: ContentVersion, output_path: Path) -> None:
        """Export version as WebVTT file."""
        def format_timestamp(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")
            
            for segment in version.segments:
                start_time = format_timestamp(segment.start_time)
                end_time = format_timestamp(segment.end_time)
                
                speaker_prefix = f"<v {segment.speaker}>" if segment.speaker else ""
                text = f"{speaker_prefix}{segment.text}"
                
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")
    
    def _export_as_json(self, version: ContentVersion, output_path: Path) -> None:
        """Export version as JSON."""
        data = {
            'version_type': version.version_type.value,
            'created_at': version.created_at.isoformat(),
            'word_count': version.word_count,
            'metadata': version.metadata,
            'full_text': version.full_text,
            'segments': [
                {
                    'start_time': seg.start_time,
                    'end_time': seg.end_time,
                    'text': seg.text,
                    'speaker': seg.speaker,
                    'confidence': seg.confidence
                }
                for seg in version.segments
            ]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format seconds to HH:MM:SS.mmm"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"
    
    def _parse_timestamp(self, time_str: str) -> float:
        """Parse HH:MM:SS.mmm to seconds"""
        try:
            parts = time_str.replace(',', '.').split(':')
            if len(parts) == 3:
                hours = float(parts[0])
                minutes = float(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
        except:
            pass
        return 0.0