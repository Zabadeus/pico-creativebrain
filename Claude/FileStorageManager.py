"""
File Storage Manager for AI Transcription & Knowledge Management Application

Provides persistent file storage with the hierarchical structure:
transcripts/
├── [session_id]/
│   ├── metadata.json          # Session info, timestamps, settings
│   ├── audio/                 # Original media files
│   │   ├── original.wav
│   │   └── segments/          # Audio chunks for timestamp mapping
│   ├── versions/              # Content versions
│   │   ├── original.md        # Raw transcript with timestamps
│   │   ├── cleaned.md         # Processed version
│   │   └── summary.md         # AI-generated summary
│   ├── knowledge/             # Knowledge management
│   │   ├── tags.json          # Auto and manual tags
│   │   ├── links.json         # Cross-references to other sessions
│   │   └── insights.md        # AI-generated insights/key points
│   └── exports/               # Generated content from this session
"""

import os
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, asdict
from enum import Enum

# Import from ContentVersionManager (assumes it's available)
try:
    from ContentVersionManager import ContentVersionManager, ContentVersion, VersionType, TimestampedSegment
except ImportError:
    # Fallback definitions if ContentVersionManager is not available
    from enum import Enum
    from dataclasses import dataclass
    from datetime import datetime
    from typing import List, Optional, Dict, Any
    
    class VersionType(Enum):
        ORIGINAL = "original"
        CLEANED = "cleaned" 
        SUMMARY_BRIEF = "summary_brief"
        SUMMARY_DETAILED = "summary_detailed"
        SUMMARY_KEYPOINTS = "summary_keypoints"


class StorageError(Exception):
    """Custom exception for storage-related errors"""
    pass


class PrivacyMode(Enum):
    """Privacy modes for content handling"""
    FULL = "full"           # Store everything
    SELECTIVE = "selective" # Store content but not audio
    METADATA_ONLY = "metadata_only"  # Store only session metadata
    NONE = "none"          # No persistent storage


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


class FileStorageManager:
    """
    Manages persistent file storage for transcription sessions with hierarchical organization.
    Integrates with ContentVersionManager for version management.
    """
    
    def __init__(self, base_path: str = "transcripts", auto_create: bool = True):
        """
        Initialize the file storage manager
        
        Args:
            base_path: Root directory for all transcript storage
            auto_create: Whether to automatically create directories
        """
        self.base_path = Path(base_path)
        self.auto_create = auto_create
        
        if auto_create:
            self._ensure_base_directory()
        
        # Directory structure templates
        self.dir_structure = {
            'metadata': 'metadata.json',
            'audio': 'audio',
            'audio_original': 'audio/original.wav',
            'audio_segments': 'audio/segments',
            'versions': 'versions',
            'knowledge': 'knowledge',
            'exports': 'exports'
        }
        
        self.version_files = {
            VersionType.ORIGINAL: 'versions/original.md',
            VersionType.CLEANED: 'versions/cleaned.md',
            VersionType.SUMMARY_BRIEF: 'versions/summary.md',
            VersionType.SUMMARY_DETAILED: 'versions/summary_detailed.md',
            VersionType.SUMMARY_KEYPOINTS: 'versions/keypoints.md'
        }
        
        self.knowledge_files = {
            'tags': 'knowledge/tags.json',
            'links': 'knowledge/links.json', 
            'insights': 'knowledge/insights.md'
        }
    
    def create_session(self, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session with directory structure
        
        Args:
            session_id: Unique session identifier (auto-generated if None)
            metadata: Initial metadata for the session
            
        Returns:
            str: The session ID
        """
        if not session_id:
            session_id = self._generate_session_id()
        
        session_path = self.base_path / session_id
        
        if session_path.exists():
            raise StorageError(f"Session {session_id} already exists")
        
        try:
            # Create directory structure
            self._create_session_directories(session_path)
            
            # Create initial metadata
            initial_metadata = SessionMetadata(
                session_id=session_id,
                created=datetime.now().isoformat(),
                updated=datetime.now().isoformat(),
                duration="00:00:00",
                speaker_count=1,
                privacy_mode=PrivacyMode.FULL.value,
                ai_processed=False
            )
            
            # Update with provided metadata
            if metadata:
                for key, value in metadata.items():
                    if hasattr(initial_metadata, key):
                        setattr(initial_metadata, key, value)
            
            # Save metadata
            self.save_session_metadata(session_id, initial_metadata)
            
            return session_id
            
        except Exception as e:
            # Cleanup on failure
            if session_path.exists():
                shutil.rmtree(session_path)
            raise StorageError(f"Failed to create session {session_id}: {str(e)}")
    
    def save_content_version(self, session_id: str, version: ContentVersion, content_manager: Optional[ContentVersionManager] = None) -> None:
        """
        Save a content version to markdown file with metadata header
        
        Args:
            session_id: Session identifier
            version: ContentVersion to save
            content_manager: Optional ContentVersionManager for additional context
        """
        session_path = self._get_session_path(session_id)
        version_file = session_path / self.version_files[version.version_type]
        
        # Ensure versions directory exists
        version_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create markdown content with metadata header
        markdown_content = self._create_markdown_with_metadata(version, session_id, content_manager)
        
        try:
            with open(version_file, 'w', encoding='utf-8') as f:
                f.write(markdown_content)
                
            # Update session metadata
            self._update_session_timestamp(session_id)
            
        except Exception as e:
            raise StorageError(f"Failed to save version {version.version_type.value} for session {session_id}: {str(e)}")
    
    def load_content_version(self, session_id: str, version_type: VersionType) -> Optional[ContentVersion]:
        """
        Load a content version from markdown file
        
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
            
            return self._parse_markdown_content(content, version_type)
            
        except Exception as e:
            raise StorageError(f"Failed to load version {version_type.value} for session {session_id}: {str(e)}")
    
    def save_audio_file(self, session_id: str, audio_data: bytes, filename: str = "original.wav") -> str:
        """
        Save audio file to session
        
        Args:
            session_id: Session identifier
            audio_data: Raw audio data
            filename: Audio filename
            
        Returns:
            str: Path to saved audio file
        """
        session_path = self._get_session_path(session_id)
        audio_dir = session_path / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        
        audio_file = audio_dir / filename
        
        try:
            with open(audio_file, 'wb') as f:
                f.write(audio_data)
            
            # Update metadata with file info
            metadata = self.load_session_metadata(session_id)
            if metadata:
                metadata.source_file = filename
                metadata.file_size = len(audio_data)
                metadata.updated = datetime.now().isoformat()
                self.save_session_metadata(session_id, metadata)
            
            return str(audio_file)
            
        except Exception as e:
            raise StorageError(f"Failed to save audio file for session {session_id}: {str(e)}")
    
    def save_audio_segments(self, session_id: str, segments: List[TimestampedSegment], segment_audio_data: Optional[Dict[str, bytes]] = None) -> None:
        """
        Save audio segments for timestamp mapping
        
        Args:
            session_id: Session identifier
            segments: List of timestamped segments
            segment_audio_data: Optional audio data for each segment
        """
        session_path = self._get_session_path(session_id)
        segments_dir = session_path / "audio" / "segments"
        segments_dir.mkdir(parents=True, exist_ok=True)
        
        # Save segment metadata
        segments_metadata = []
        for i, segment in enumerate(segments):
            segment_data = {
                'index': i,
                'start_time': segment.start_time,
                'end_time': segment.end_time,
                'text': segment.text,
                'speaker': segment.speaker,
                'confidence': segment.confidence,
                'filename': f"segment_{i:04d}.wav" if segment_audio_data else None
            }
            segments_metadata.append(segment_data)
            
            # Save individual segment audio if provided
            if segment_audio_data and f"segment_{i}" in segment_audio_data:
                segment_file = segments_dir / f"segment_{i:04d}.wav"
                with open(segment_file, 'wb') as f:
                    f.write(segment_audio_data[f"segment_{i}"])
        
        # Save segments index
        segments_index_file = segments_dir / "segments_index.json"
        with open(segments_index_file, 'w', encoding='utf-8') as f:
            json.dump(segments_metadata, f, indent=2)
    
    def save_knowledge_data(self, session_id: str, knowledge: KnowledgeData) -> None:
        """
        Save knowledge management data
        
        Args:
            session_id: Session identifier
            knowledge: KnowledgeData to save
        """
        session_path = self._get_session_path(session_id)
        knowledge_dir = session_path / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            # Save tags
            tags_data = {
                'all_tags': knowledge.tags,
                'auto_tags': knowledge.auto_tags,
                'manual_tags': knowledge.manual_tags,
                'topics': knowledge.topics,
                'created': knowledge.created,
                'updated': knowledge.updated
            }
            with open(knowledge_dir / "tags.json", 'w', encoding='utf-8') as f:
                json.dump(tags_data, f, indent=2)
            
            # Save links
            with open(knowledge_dir / "links.json", 'w', encoding='utf-8') as f:
                json.dump(knowledge.links, f, indent=2)
            
            # Save insights as markdown
            insights_content = f"# Insights - {session_id}\n\n"
            insights_content += f"**Generated:** {knowledge.created}\n"
            insights_content += f"**Updated:** {knowledge.updated}\n\n"
            
            if knowledge.key_points:
                insights_content += "## Key Points\n\n"
                for point in knowledge.key_points:
                    insights_content += f"- {point}\n"
                insights_content += "\n"
            
            if knowledge.insights:
                insights_content += "## Detailed Insights\n\n"
                for insight in knowledge.insights:
                    insights_content += f"{insight}\n\n"
            
            with open(knowledge_dir / "insights.md", 'w', encoding='utf-8') as f:
                f.write(insights_content)
                
        except Exception as e:
            raise StorageError(f"Failed to save knowledge data for session {session_id}: {str(e)}")
    
    def load_knowledge_data(self, session_id: str) -> Optional[KnowledgeData]:
        """
        Load knowledge management data
        
        Args:
            session_id: Session identifier
            
        Returns:
            KnowledgeData or None if not found
        """
        session_path = self._get_session_path(session_id)
        knowledge_dir = session_path / "knowledge"
        
        if not knowledge_dir.exists():
            return None
        
        try:
            # Load tags
            tags_file = knowledge_dir / "tags.json"
            if tags_file.exists():
                with open(tags_file, 'r', encoding='utf-8') as f:
                    tags_data = json.load(f)
            else:
                tags_data = {'all_tags': [], 'auto_tags': [], 'manual_tags': [], 'topics': []}
            
            # Load links
            links_file = knowledge_dir / "links.json"
            if links_file.exists():
                with open(links_file, 'r', encoding='utf-8') as f:
                    links_data = json.load(f)
            else:
                links_data = {}
            
            # Load insights (parse from markdown)
            insights_file = knowledge_dir / "insights.md"
            insights = []
            key_points = []
            created = updated = datetime.now().isoformat()
            
            if insights_file.exists():
                with open(insights_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                insights, key_points, created, updated = self._parse_insights_markdown(content)
            
            return KnowledgeData(
                tags=tags_data.get('all_tags', []),
                auto_tags=tags_data.get('auto_tags', []),
                manual_tags=tags_data.get('manual_tags', []),
                links=links_data,
                insights=insights,
                key_points=key_points,
                topics=tags_data.get('topics', []),
                created=created,
                updated=updated
            )
            
        except Exception as e:
            raise StorageError(f"Failed to load knowledge data for session {session_id}: {str(e)}")
    
    def save_session_metadata(self, session_id: str, metadata: SessionMetadata) -> None:
        """Save session metadata"""
        session_path = self._get_session_path(session_id)
        metadata_file = session_path / "metadata.json"
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(metadata), f, indent=2)
        except Exception as e:
            raise StorageError(f"Failed to save metadata for session {session_id}: {str(e)}")
    
    def load_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """Load session metadata"""
        session_path = self._get_session_path(session_id)
        metadata_file = session_path / "metadata.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SessionMetadata(**data)
        except Exception as e:
            raise StorageError(f"Failed to load metadata for session {session_id}: {str(e)}")
    
    def export_session(self, session_id: str, export_format: str, include_audio: bool = True) -> str:
        """
        Export complete session in specified format
        
        Args:
            session_id: Session identifier
            export_format: Export format ('json', 'zip', 'html')
            include_audio: Whether to include audio files
            
        Returns:
            str: Path to exported file
        """
        session_path = self._get_session_path(session_id)
        exports_dir = session_path / "exports"
        exports_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if export_format == 'json':
            return self._export_session_json(session_id, exports_dir, timestamp, include_audio)
        elif export_format == 'zip':
            return self._export_session_zip(session_id, exports_dir, timestamp, include_audio)
        elif export_format == 'html':
            return self._export_session_html(session_id, exports_dir, timestamp)
        else:
            raise ValueError(f"Unsupported export format: {export_format}")
    
    def list_sessions(self, include_metadata: bool = False) -> List[Union[str, Dict[str, Any]]]:
        """
        List all available sessions
        
        Args:
            include_metadata: Whether to include metadata for each session
            
        Returns:
            List of session IDs or session info with metadata
        """
        if not self.base_path.exists():
            return []
        
        sessions = []
        for item in self.base_path.iterdir():
            if item.is_dir() and (item / "metadata.json").exists():
                if include_metadata:
                    metadata = self.load_session_metadata(item.name)
                    sessions.append({
                        'session_id': item.name,
                        'metadata': asdict(metadata) if metadata else None
                    })
                else:
                    sessions.append(item.name)
        
        return sessions
    
    def delete_session(self, session_id: str, confirm: bool = False) -> None:
        """
        Delete a session and all its data
        
        Args:
            session_id: Session identifier
            confirm: Safety confirmation flag
        """
        if not confirm:
            raise StorageError("Session deletion requires explicit confirmation")
        
        session_path = self._get_session_path(session_id)
        
        if not session_path.exists():
            raise StorageError(f"Session {session_id} does not exist")
        
        try:
            shutil.rmtree(session_path)
        except Exception as e:
            raise StorageError(f"Failed to delete session {session_id}: {str(e)}")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a session"""
        session_path = self._get_session_path(session_id)
        
        if not session_path.exists():
            raise StorageError(f"Session {session_id} does not exist")
        
        stats = {
            'session_id': session_id,
            'total_size_bytes': self._get_directory_size(session_path),
            'files_count': len(list(session_path.rglob('*'))),
            'directories': {},
            'versions_available': [],
            'has_audio': False,
            'has_knowledge_data': False
        }
        
        # Check each directory
        for dir_name in ['audio', 'versions', 'knowledge', 'exports']:
            dir_path = session_path / dir_name
            if dir_path.exists():
                stats['directories'][dir_name] = {
                    'exists': True,
                    'files_count': len(list(dir_path.rglob('*'))),
                    'size_bytes': self._get_directory_size(dir_path)
                }
        
        # Check available versions
        versions_dir = session_path / "versions"
        if versions_dir.exists():
            for version_type, filename in self.version_files.items():
                if (session_path / filename).exists():
                    stats['versions_available'].append(version_type.value)
        
        # Check for audio and knowledge data
        stats['has_audio'] = (session_path / "audio" / "original.wav").exists()
        stats['has_knowledge_data'] = (session_path / "knowledge").exists()
        
        return stats
    
    # Private helper methods
    
    def _ensure_base_directory(self) -> None:
        """Ensure base directory exists"""
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _generate_session_id(self) -> str:
        """Generate a unique session ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")
    
    def _get_session_path(self, session_id: str) -> Path:
        """Get path to session directory"""
        return self.base_path / session_id
    
    def _create_session_directories(self, session_path: Path) -> None:
        """Create the complete directory structure for a session"""
        directories = [
            session_path,
            session_path / "audio",
            session_path / "audio" / "segments", 
            session_path / "versions",
            session_path / "knowledge",
            session_path / "exports"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _create_markdown_with_metadata(self, version: ContentVersion, session_id: str, content_manager: Optional[ContentVersionManager]) -> str:
        """Create markdown content with YAML front matter metadata"""
        metadata = {
            'version': version.version_type.value,
            'session_id': session_id,
            'duration': self._format_duration(version.segments),
            'speaker_count': len(set(seg.speaker for seg in version.segments if seg.speaker)),
            'word_count': version.word_count,
            'created': version.created_at.isoformat(),
            'ai_processed': True,
            'segment_count': len(version.segments)
        }
        
        # Add version-specific metadata
        metadata.update(version.metadata)
        
        # Create YAML front matter
        yaml_header = "---\n"
        for key, value in metadata.items():
            if isinstance(value, str):
                yaml_header += f'{key}: "{value}"\n'
            else:
                yaml_header += f'{key}: {value}\n'
        yaml_header += "---\n\n"
        
        # Create content
        title = f"# Transcript: {version.version_type.value.title()} Version\n\n"
        
        content = ""
        if version.segments:
            for segment in version.segments:
                timestamp = self._format_timestamp(segment.start_time)
                speaker = f" {segment.speaker}" if segment.speaker else ""
                content += f"## [{timestamp}]{speaker}\n{segment.text}\n\n"
        else:
            content = version.full_text
        
        return yaml_header + title + content
    
    def _parse_markdown_content(self, content: str, version_type: VersionType) -> ContentVersion:
        """Parse markdown content back into ContentVersion"""
        lines = content.split('\n')
        
        # Parse YAML front matter
        if lines[0] == '---':
            yaml_end = next(i for i, line in enumerate(lines[1:], 1) if line == '---')
            metadata_lines = lines[1:yaml_end]
            content_lines = lines[yaml_end+1:]
            
            metadata = {}
            for line in metadata_lines:
                if ':' in line:
                    key, value = line.split(':', 1)
                    key = key.strip()
                    value = value.strip().strip('"')
                    try:
                        # Try to convert to appropriate type
                        if value.lower() in ('true', 'false'):
                            metadata[key] = value.lower() == 'true'
                        elif value.isdigit():
                            metadata[key] = int(value)
                        elif '.' in value and value.replace('.', '').isdigit():
                            metadata[key] = float(value)
                        else:
                            metadata[key] = value
                    except:
                        metadata[key] = value
        else:
            content_lines = lines
            metadata = {}
        
        # Parse content and segments
        full_text = '\n'.join(content_lines)
        segments = self._parse_segments_from_markdown(content_lines)
        
        # Create ContentVersion
        return ContentVersion(
            version_type=version_type,
            segments=segments,
            full_text=full_text,
            metadata=metadata,
            created_at=datetime.fromisoformat(metadata.get('created', datetime.now().isoformat())),
            word_count=metadata.get('word_count', len(full_text.split()))
        )
    
    def _parse_segments_from_markdown(self, content_lines: List[str]) -> List[TimestampedSegment]:
        """Parse timestamped segments from markdown content"""
        segments = []
        current_segment = None
        
        for line in content_lines:
            # Look for timestamp headers like "## [00:01:23] Speaker 1"
            if line.startswith('## [') and ']' in line:
                if current_segment:
                    segments.append(current_segment)
                
                # Parse timestamp and speaker
                timestamp_end = line.find(']')
                timestamp_str = line[4:timestamp_end]
                speaker_part = line[timestamp_end+1:].strip()
                
                start_time = self._parse_timestamp(timestamp_str)
                speaker = speaker_part if speaker_part else None
                
                current_segment = {
                    'start_time': start_time,
                    'end_time': start_time,  # Will be updated
                    'text': '',
                    'speaker': speaker
                }
            
            elif current_segment and line.strip() and not line.startswith('#'):
                # Add text to current segment
                if current_segment['text']:
                    current_segment['text'] += ' ' + line.strip()
                else:
                    current_segment['text'] = line.strip()
        
        # Add final segment
        if current_segment:
            segments.append(current_segment)
        
        # Convert to TimestampedSegment objects and estimate end times
        result_segments = []
        for i, seg_data in enumerate(segments):
            end_time = segments[i+1]['start_time'] if i+1 < len(segments) else seg_data['start_time'] + 5.0
            
            segment = TimestampedSegment(
                start_time=seg_data['start_time'],
                end_time=end_time,
                text=seg_data['text'],
                speaker=seg_data['speaker']
            )
            result_segments.append(segment)
        
        return result_segments
    
    def _parse_insights_markdown(self, content: str) -> tuple:
        """Parse insights markdown content"""
        lines = content.split('\n')
        insights = []
        key_points = []
        created = updated = datetime.now().isoformat()
        
        current_section = None
        
        for line in lines:
            if '**Generated:**' in line:
                created = line.split('**Generated:**')[1].strip()
            elif '**Updated:**' in line:
                updated = line.split('**Updated:**')[1].strip()
            elif line.startswith('## Key Points'):
                current_section = 'key_points'
            elif line.startswith('## Detailed Insights'):
                current_section = 'insights'
            elif line.startswith('- ') and current_section == 'key_points':
                key_points.append(line[2:].strip())
            elif line.strip() and current_section == 'insights' and not line.startswith('#'):
                insights.append(line.strip())
        
        return insights, key_points, created, updated
    
    def _format_duration(self, segments: List[TimestampedSegment]) -> str:
        """Format duration from segments"""
        if not segments:
            return "00:00:00"
        
        total_seconds = segments[-1].end_time
        hours = int(total_seconds // 3600)
        minutes = int((total_seconds % 3600) // 60)
        seconds = int(total_seconds % 60)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    
    def _format_timestamp(self, seconds: float) -> str:
        """Format timestamp for display"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def _parse_timestamp(self, timestamp_str: str) -> float:
        """Parse timestamp string to seconds"""
        parts = timestamp_str.split(':')
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0.0
    
    def _update_session_timestamp(self, session_id: str) -> None:
        """Update session's last modified timestamp"""
        metadata = self.load_session_metadata(session_id)
        if metadata:
            metadata.updated = datetime.now().isoformat()
            self.save_session_metadata(session_id, metadata)
    
    def _get_directory_size(self, path: Path) -> int:
        """Calculate total size of directory"""
        total_size = 0
        for file_path in path.rglob('*'):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size
    
    def _export_session_json(self, session_id: str,