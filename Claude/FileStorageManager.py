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
    
    def _export_session_json(self, session_id: str, exports_dir: Path, timestamp: str, include_audio: bool = True) -> str:
        """Export session as comprehensive JSON file"""
        export_file = exports_dir / f"session_{session_id}_{timestamp}.json"
        
        try:
            # Collect all session data
            export_data = {
                'session_id': session_id,
                'export_timestamp': datetime.now().isoformat(),
                'export_format': 'json',
                'metadata': None,
                'content_versions': {},
                'knowledge_data': None,
                'audio_info': {},
                'segments_info': None,
                'stats': None
            }
            
            # Load metadata
            metadata = self.load_session_metadata(session_id)
            if metadata:
                export_data['metadata'] = asdict(metadata)
            
            # Load all content versions
            for version_type in VersionType:
                version = self.load_content_version(session_id, version_type)
                if version:
                    # Convert segments to serializable format
                    segments_data = []
                    for segment in version.segments:
                        segments_data.append({
                            'start_time': segment.start_time,
                            'end_time': segment.end_time,
                            'text': segment.text,
                            'speaker': segment.speaker,
                            'confidence': getattr(segment, 'confidence', 1.0)
                        })
                    
                    export_data['content_versions'][version_type.value] = {
                        'full_text': version.full_text,
                        'segments': segments_data,
                        'word_count': version.word_count,
                        'created_at': version.created_at.isoformat(),
                        'metadata': version.metadata
                    }
            
            # Load knowledge data
            knowledge = self.load_knowledge_data(session_id)
            if knowledge:
                export_data['knowledge_data'] = asdict(knowledge)
            
            # Audio information (metadata only, not raw data unless specifically requested)
            session_path = self._get_session_path(session_id)
            audio_dir = session_path / "audio"
            if audio_dir.exists():
                original_audio = audio_dir / "original.wav"
                if original_audio.exists():
                    stat = original_audio.stat()
                    export_data['audio_info'] = {
                        'has_original': True,
                        'file_size_bytes': stat.st_size,
                        'file_modified': datetime.fromtimestamp(stat.st_mtime).isoformat()
                    }
                    
                    # Include audio as base64 if requested (be careful with large files!)
                    if include_audio and stat.st_size < 50 * 1024 * 1024:  # Only if < 50MB
                        import base64
                        with open(original_audio, 'rb') as f:
                            export_data['audio_info']['audio_data_base64'] = base64.b64encode(f.read()).decode('utf-8')
                
                # Load segments info
                segments_index = audio_dir / "segments" / "segments_index.json"
                if segments_index.exists():
                    with open(segments_index, 'r', encoding='utf-8') as f:
                        export_data['segments_info'] = json.load(f)
            
            # Session statistics
            export_data['stats'] = self.get_session_stats(session_id)
            
            # Write JSON export
            with open(export_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            return str(export_file)
            
        except Exception as e:
            raise StorageError(f"Failed to export session {session_id} as JSON: {str(e)}")
    
    def _export_session_zip(self, session_id: str, exports_dir: Path, timestamp: str, include_audio: bool = True) -> str:
        """Export complete session as ZIP archive"""
        import zipfile
        
        export_file = exports_dir / f"session_{session_id}_{timestamp}.zip"
        session_path = self._get_session_path(session_id)
        
        try:
            with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in session_path.rglob('*'):
                    if file_path.is_file():
                        # Skip audio files if not requested
                        if not include_audio and 'audio/' in str(file_path.relative_to(session_path)):
                            continue
                        
                        # Skip the exports directory to avoid recursive inclusion
                        if 'exports/' in str(file_path.relative_to(session_path)):
                            continue
                        
                        # Add file to zip with relative path
                        arcname = str(file_path.relative_to(session_path))
                        zipf.write(file_path, arcname)
                
                # Add export manifest
                manifest = {
                    'session_id': session_id,
                    'export_timestamp': datetime.now().isoformat(),
                    'export_format': 'zip',
                    'includes_audio': include_audio,
                    'exported_by': 'FileStorageManager',
                    'structure': {
                        'metadata.json': 'Session metadata and settings',
                        'audio/': 'Original audio files and segments' if include_audio else 'Not included',
                        'versions/': 'Content versions (original, cleaned, summaries)',
                        'knowledge/': 'Tags, links, and insights data'
                    }
                }
                
                zipf.writestr('export_manifest.json', json.dumps(manifest, indent=2))
            
            return str(export_file)
            
        except Exception as e:
            raise StorageError(f"Failed to export session {session_id} as ZIP: {str(e)}")
    
    def _export_session_html(self, session_id: str, exports_dir: Path, timestamp: str) -> str:
        """Export session as interactive HTML report"""
        export_file = exports_dir / f"session_{session_id}_{timestamp}.html"
        
        try:
            # Load session data
            metadata = self.load_session_metadata(session_id)
            knowledge = self.load_knowledge_data(session_id)
            stats = self.get_session_stats(session_id)
            
            # Load content versions
            versions = {}
            for version_type in VersionType:
                version = self.load_content_version(session_id, version_type)
                if version:
                    versions[version_type.value] = version
            
            # Generate HTML content
            html_content = self._generate_html_template(session_id, metadata, knowledge, versions, stats, timestamp)
            
            with open(export_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            return str(export_file)
            
        except Exception as e:
            raise StorageError(f"Failed to export session {session_id} as HTML: {str(e)}")
    
    def _generate_html_template(self, session_id: str, metadata: Optional[SessionMetadata], 
                               knowledge: Optional[KnowledgeData], versions: Dict[str, Any], 
                               stats: Dict[str, Any], timestamp: str) -> str:
        """Generate HTML template for session export"""
        
        # Create HTML structure
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Session Report: {session_id}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .header .meta {{ opacity: 0.9; margin-top: 10px; }}
        
        .content {{
            background: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .version-tabs {{
            display: flex;
            background: #f8f9fa;
            border-radius: 8px;
            padding: 4px;
            margin-bottom: 20px;
        }}
        
        .version-tab {{
            flex: 1;
            padding: 10px 20px;
            background: transparent;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
            transition: all 0.3s;
        }}
        
        .version-tab.active {{
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            color: #667eea;
        }}
        
        .version-content {{
            display: none;
            animation: fadeIn 0.3s;
        }}
        
        .version-content.active {{ display: block; }}
        
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(10px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        
        .segment {{
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-left: 4px solid #667eea;
            border-radius: 0 8px 8px 0;
        }}
        
        .segment-header {{
            font-weight: bold;
            color: #667eea;
            margin-bottom: 8px;
            font-size: 0.9em;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            text-align: center;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
            margin-bottom: 5px;
        }}
        
        .stat-label {{
            color: #666;
            font-size: 0.9em;
        }}
        
        .tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }}
        
        .tag {{
            background: #e3f2fd;
            color: #1976d2;
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.85em;
            font-weight: 500;
        }}
        
        .auto-tag {{ background: #f3e5f5; color: #7b1fa2; }}
        .manual-tag {{ background: #e8f5e8; color: #388e3c; }}
        
        .insights ul {{
            list-style: none;
            padding: 0;
        }}
        
        .insights li {{
            background: #f8f9fa;
            padding: 12px;
            margin-bottom: 8px;
            border-radius: 6px;
            border-left: 3px solid #28a745;
        }}
        
        .export-info {{
            background: #e7f3ff;
            border: 1px solid #b8daff;
            padding: 15px;
            border-radius: 8px;
            margin-top: 30px;
            font-size: 0.9em;
            color: #004085;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📝 Session Report</h1>
        <div class="meta">
            <strong>Session ID:</strong> {session_id}<br>
            <strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}<br>
            <strong>Duration:</strong> {metadata.duration if metadata else 'Unknown'}<br>
            <strong>Privacy Mode:</strong> {metadata.privacy_mode if metadata else 'Unknown'}
        </div>
    </div>"""
        
        # Add statistics
        if stats:
            html += f"""
    <div class="content">
        <h2>📊 Session Statistics</h2>
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-number">{len(versions)}</div>
                <div class="stat-label">Content Versions</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{stats.get('files_count', 0)}</div>
                <div class="stat-label">Total Files</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{self._format_file_size(stats.get('total_size_bytes', 0))}</div>
                <div class="stat-label">Total Size</div>
            </div>
            <div class="stat-card">
                <div class="stat-number">{'✅' if stats.get('has_audio') else '❌'}</div>
                <div class="stat-label">Has Audio</div>
            </div>
        </div>
    </div>"""
        
        # Add knowledge data
        if knowledge:
            html += f"""
    <div class="content">
        <h2>🧠 Knowledge & Insights</h2>
        
        <h3>Tags & Topics</h3>
        <div class="tags">"""
            
            for tag in knowledge.auto_tags:
                html += f'<span class="tag auto-tag">🤖 {tag}</span>'
            
            for tag in knowledge.manual_tags:
                html += f'<span class="tag manual-tag">👤 {tag}</span>'
                
            html += """</div>
        
        <h3>Key Insights</h3>
        <div class="insights">"""
            
            if knowledge.key_points:
                html += "<ul>"
                for point in knowledge.key_points:
                    html += f"<li>{point}</li>"
                html += "</ul>"
            
            if knowledge.insights:
                for insight in knowledge.insights:
                    html += f"<p>{insight}</p>"
                    
            html += """</div>
    </div>"""
        
        # Add content versions
        if versions:
            html += """
    <div class="content">
        <h2>📄 Content Versions</h2>
        
        <div class="version-tabs">"""
            
            for i, (version_name, version_data) in enumerate(versions.items()):
                active_class = "active" if i == 0 else ""
                html += f'<button class="version-tab {active_class}" onclick="switchVersion(\'{version_name}\')">{version_name.title()}</button>'
            
            html += "</div>"
            
            for i, (version_name, version_data) in enumerate(versions.items()):
                active_class = "active" if i == 0 else ""
                html += f"""
        <div class="version-content {active_class}" id="version-{version_name}">
            <div style="margin-bottom: 15px; color: #666;">
                <strong>Word Count:</strong> {version_data.word_count} | 
                <strong>Created:</strong> {version_data.created_at.strftime('%Y-%m-%d %H:%M')}
            </div>"""
                
                if version_data.segments:
                    for segment in version_data.segments:
                        speaker_info = f" - {segment.speaker}" if segment.speaker else ""
                        html += f"""
            <div class="segment">
                <div class="segment-header">[{self._format_timestamp(segment.start_time)}]{speaker_info}</div>
                <div>{segment.text}</div>
            </div>"""
                else:
                    # Show full text if no segments
                    html += f'<div style="white-space: pre-wrap; background: #f8f9fa; padding: 20px; border-radius: 8px;">{version_data.full_text}</div>'
                
                html += "</div>"
        
        # Add JavaScript for version switching
        html += """
    </div>
    
    <div class="export-info">
        <strong>Export Information:</strong><br>
        This HTML report was generated from your PICO Creative Brain session data. 
        All content is self-contained in this file for easy sharing and archiving.
        Generated on """ + timestamp + """ using FileStorageManager v1.0
    </div>
    
    <script>
        function switchVersion(versionName) {
            // Hide all version contents
            document.querySelectorAll('.version-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Remove active class from all tabs
            document.querySelectorAll('.version-tab').forEach(tab => {
                tab.classList.remove('active');
            });
            
            // Show selected version content
            document.getElementById('version-' + versionName).classList.add('active');
            
            // Activate selected tab
            event.target.classList.add('active');
        }
    </script>
</body>
</html>"""
        
        return html
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human readable format"""
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.1f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.1f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"
    
    def backup_session(self, session_id: str, backup_location: Optional[str] = None) -> str:
        """
        Create a backup of a session
        
        Args:
            session_id: Session identifier
            backup_location: Optional custom backup location
            
        Returns:
            str: Path to backup file
        """
        if backup_location:
            backup_dir = Path(backup_location)
        else:
            backup_dir = self.base_path / "backups"
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_dir / f"backup_{session_id}_{timestamp}.zip"
        
        try:
            # Use ZIP export functionality
            temp_exports_dir = self.base_path / session_id / "exports"
            temp_exports_dir.mkdir(exist_ok=True)
            
            zip_path = self._export_session_zip(session_id, temp_exports_dir, timestamp, include_audio=True)
            
            # Move to backup location
            shutil.move(zip_path, backup_file)
            
            return str(backup_file)
            
        except Exception as e:
            raise StorageError(f"Failed to backup session {session_id}: {str(e)}")
    
    def restore_session(self, backup_file: str, new_session_id: Optional[str] = None) -> str:
        """
        Restore a session from backup
        
        Args:
            backup_file: Path to backup ZIP file
            new_session_id: Optional new session ID (auto-generated if None)
            
        Returns:
            str: The restored session ID
        """
        import zipfile
        
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise StorageError(f"Backup file not found: {backup_file}")
        
        if not new_session_id:
            new_session_id = self._generate_session_id()
        
        session_path = self.base_path / new_session_id
        
        if session_path.exists():
            raise StorageError(f"Session {new_session_id} already exists")
        
        try:
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(session_path)
            
            # Update session ID in metadata if it was restored with a new ID
            metadata_file = session_path / "metadata.json"
            if metadata_file.exists():
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata_data = json.load(f)
                
                original_session_id = metadata_data.get('session_id')
                metadata_data['session_id'] = new_session_id
                metadata_data['restored_from'] = original_session_id
                metadata_data['restored_at'] = datetime.now().isoformat()
                
                with open(metadata_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata_data, f, indent=2)
            
            return new_session_id
            
        except Exception as e:
            # Cleanup on failure
            if session_path.exists():
                shutil.rmtree(session_path)
            raise StorageError(f"Failed to restore session from {backup_file}: {str(e)}")
    
    def cleanup_old_exports(self, session_id: str, keep_latest: int = 3) -> int:
        """
        Clean up old export files, keeping only the latest N files
        
        Args:
            session_id: Session identifier
            keep_latest: Number of latest export files to keep
            
        Returns:
            int: Number of files deleted
        """
        session_path = self._get_session_path(session_id)
        exports_dir = session_path / "exports"
        
        if not exports_dir.exists():
            return 0
        
        # Get all export files with their modification times
        export_files = []
        for file_path in exports_dir.glob("session_*"):
            if file_path.is_file():
                export_files.append((file_path, file_path.stat().st_mtime))
        
        # Sort by modification time (newest first)
        export_files.sort(key=lambda x: x[1], reverse=True)
        
        # Delete old files
        deleted_count = 0
        for file_path, _ in export_files[keep_latest:]:
            try:
                file_path.unlink()
                deleted_count += 1
            except Exception:
                pass  # Skip files that can't be deleted
        
        return deleted_count
    
    def validate_session_integrity(self, session_id: str) -> Dict[str, Any]:
        """
        Validate session data integrity and return status report
        
        Args:
            session_id: Session identifier
            
        Returns:
            Dict with validation results
        """
        session_path = self._get_session_path(session_id)
        
        validation_result = {
            'session_id': session_id,
            'valid': True,
            'errors': [],
            'warnings': [],
            'checks': {
                'metadata_exists': False,
                'metadata_valid': False,
                'versions_consistent': False,
                'knowledge_data_valid': False,
                'audio_files_accessible': False,
                'directory_structure_complete': False
            }
        }
        
        try:
            # Check if session exists
            if not session_path.exists():
                validation_result['valid'] = False
                validation_result['errors'].append("Session directory does not exist")
                return validation_result
            
            # Check metadata
            metadata_file = session_path / "metadata.json"
            if metadata_file.exists():
                validation_result['checks']['metadata_exists'] = True
                try:
                    metadata = self.load_session_metadata(session_id)
                    if metadata:
                        validation_result['checks']['metadata_valid'] = True
                    else:
                        validation_result['warnings'].append("Metadata file exists but could not be loaded")
                except Exception as e:
                    validation_result['warnings'].append(f"Metadata validation failed: {str(e)}")
            else:
                validation_result['errors'].append("Metadata file missing")
                validation_result['valid'] = False
            
            # Check directory structure
            required_dirs = ['audio', 'versions', 'knowledge', 'exports']
            missing_dirs = []
            for dir_name in required_dirs:
                if not (session_path / dir_name).exists():
                    missing_dirs.append(dir_name)
            
            if not missing_dirs:
                validation_result['checks']['directory_structure_complete'] = True
            else:
                validation_result['warnings'].append(f"Missing directories: {', '.join(missing_dirs)}")
            
            # Check content versions consistency
            versions_consistent = True
            for version_type in VersionType:
                try:
                    version = self.load_content_version(session_id, version_type)
                    if version and hasattr(version, 'segments') and version.segments:
                        # Basic consistency checks
                        if version.word_count <= 0:
                            versions_consistent = False
                            validation_result['warnings'].append(f"Version {version_type.value} has invalid word count")
                except Exception as e:
                    validation_result['warnings'].append(f"Could not validate version {version_type.value}: {str(e)}")
                    versions_consistent = False
            
            validation_result['checks']['versions_consistent'] = versions_consistent
            
            # Check knowledge data
            try:
                knowledge = self.load_knowledge_data(session_id)
                if knowledge:
                    validation_result['checks']['knowledge_data_valid'] = True
            except Exception as e:
                validation_result['warnings'].append(f"Knowledge data validation failed: {str(e)}")
            
            # Check audio files
            audio_dir = session_path / "audio"
            if audio_dir.exists():
                original_audio = audio_dir / "original.wav"
                if original_audio.exists() and original_audio.stat().st_size > 0:
                    validation_result['checks']['audio_files_accessible'] = True
                else:
                    validation_result['warnings'].append("Audio directory exists but no valid audio file found")
            
            # Final validation status
            if validation_result['errors']:
                validation_result['valid'] = False
            
        except Exception as e:
            validation_result['valid'] = False
            validation_result['errors'].append(f"Validation process failed: {str(e)}")
        
        return validation_result