# PICO - AI Transcription & Second Brain App - Streamlined Build Guide

## 🎯 Project Vision

PICO (Processing Ideas Creating Output) - Cross-platform second-brain app for audio transcription with AI-powered content management and generation.

## 📊 Implementation Status (90% Backend Complete)

### ✅ FULLY IMPLEMENTED (Production Ready)

- **TranscriptionEngine.py**: faster-whisper + GPU acceleration + speaker diarization + word-level timestamps
- **UniversalInputHandler.py**: Live recording + YouTube/podcast processing + all audio formats
- **ContentVersionManager.py**: Original→Cleaned→Summary versions + multi-format export (JSON/SRT/VTT/TXT)
- **PrivacyManager.py**: GDPR-compliant privacy modes + PII detection + AI usage tracking
- **FileStorageManager.py**: Complete session lifecycle + file structure + knowledge management + session exports

### ❌ MISSING (Critical Path)

- **Flutter Frontend**: 0% complete - PRIMARY BLOCKER
- **AI Provider APIs**: Framework exists, need OpenAI/Claude/Gemini integrations
- **Knowledge Graph**: Database + semantic linking system
- **Testing Framework**: Unit/integration tests

## 🏗️ Architecture

### Data Flow

```
Audio Input → Whisper Transcription → Version Manager (Original/Cleaned/Summary) → AI Enhancement
     ↓                                       ↓                                    ↓
Privacy Check → Speaker Diarization → FileStorageManager (Sessions/Knowledge) → Export
                        ↓                         ↓
              Timestamp Preservation → Knowledge Linking (tags/insights/cross-refs)
```

### File Structure (Markdown-based - Managed by FileStorageManager)

```
transcripts/[session_id]/
├── metadata.json          # Session info, privacy settings, AI usage
├── audio/                 # original.wav + segments/ for timestamp mapping
├── versions/              # original.md, cleaned.md, summary.md
├── knowledge/             # tags.json, links.json, insights.md (AI-generated)
└── exports/               # Session packages (JSON/ZIP/HTML)
```

### Core Classes & Methods

```python
# TranscriptionEngine: transcribe(), get_speakers(), get_timestamps()
# UniversalInputHandler: process_file(), record_live(), download_youtube()
# ContentVersionManager: switch_version(), clean_text(), export_format()
# PrivacyManager: check_privacy(), log_ai_usage(), detect_pii()
# FileStorageManager: create_session(), load_session(), save_knowledge(), export_session()
```

### Export Functionality Split

- **ContentVersionManager**: Format exports (SRT/VTT/TXT/JSON) for individual transcripts
- **FileStorageManager**: Session exports (JSON/ZIP/HTML) for complete project packages

## 🚨 IMMEDIATE PRIORITIES

### 1. Flutter Frontend (CRITICAL - Weeks 1-2)

**Components Needed:**

- Main transcript view with version switching (Original/Cleaned/Summary)
- Media player with timestamp sync + click-to-jump
- File upload/URL input + live recording controls
- Multi-document tabs + side-by-side views
- Privacy dashboard + AI usage monitor
- Speaker management (rename Speaker 1→"Max", etc.)

**UI Specifications:**

- VSCode/Obsidian-style layout
- Left sidebar: File management + transcription + content creation + settings
- Header: Show/hide panels, search bar
- Multi-window support with synchronized highlighting
- Dark/light themes + customizable colors
- Context menu: Show original/cleaned/summary versions
- Drag-and-drop file upload

### 2. AI Integration (HIGH - Week 3)

**APIs to Connect:**

- OpenAI GPT-4 for content enhancement
- Claude for analysis/summarization
- Google Gemini for additional AI processing
- Local LLM support (llama.cpp)
- Connect to existing ContentVersionManager

### 3. Essential Features (Weeks 4-5)

- Bulk transcription processing
- Template system for automation workflows
- Cloud sync (Google Drive/OneDrive/iCloud)
- Calendar integration + timer/reminders
- Word count + analytics
- Speaker naming/management

## ⚙️ Technical Implementation Notes

### Flutter-Python Bridge

- Use `flutter_python` package or platform channels
- Python services run as background processes
- JSON communication for transcription data

### Privacy Implementation

- Three modes: PRIVATE (no AI), SELECTIVE (user approval), OPEN (full AI)
- Real-time PII scanning before AI processing
- Detailed usage logging with GDPR compliance

### Performance Optimizations

- GPU acceleration for Whisper (CUDA/MPS/CPU fallback)
- Chunked processing for large files
- Background transcription with progress callbacks
- Efficient timestamp indexing for instant seeking

### Export Formats

- Standard: TXT, SRT, VTT, JSON
- Custom: Markdown with metadata headers
- Integration-ready: Obsidian-compatible format

## 🎯 Success Metrics

- **Current Backend**: 90% complete (all core modules implemented)
- **Target Phase 1**: Flutter MVP with core transcription UI
- **Target Phase 2**: Full version management + AI integration
- **Target Phase 3**: Knowledge graph + advanced features

## 💡 Key Design Decisions

- Markdown-first storage for human readability + AI processing
- Privacy-by-design with granular controls
- Timestamp preservation across all content versions
- Modular architecture for easy feature additions
- Cross-platform compatibility (Windows/macOS/iOS/Web)

---

**Next Action**: Begin Flutter frontend development - backend is ready to support full-featured UI.

"""
File Storage Manager for AI Transcription & Knowledge Management Application

Provides persistent file storage with the hierarchical structure:
transcripts/
├── [session_id]/
│ ├── metadata.json # Session info, timestamps, settings
│ ├── audio/ # Original media files
│ │ ├── original.wav
│ │ └── segments/ # Audio chunks for timestamp mapping
│ ├── versions/ # Content versions
│ │ ├── original.md # Raw transcript with timestamps
│ │ ├── cleaned.md # Processed version
│ │ └── summary.md # AI-generated summary
│ ├── knowledge/ # Knowledge management
│ │ ├── tags.json # Auto and manual tags
│ │ ├── links.json # Cross-references to other sessions
│ │ └── insights.md # AI-generated insights/key points
│ └── exports/ # Generated content from this session
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
except ImportError: # Fallback definitions if ContentVersionManager is not available
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
FULL = "full" # Store everything
SELECTIVE = "selective" # Store content but not audio
METADATA_ONLY = "metadata_only" # Store only session metadata
NONE = "none" # No persistent storage

@dataclass
class SessionMetadata:
"""Session metadata structure"""
session_id: str
created: str # ISO format datetime
updated: str # ISO format datetime
duration: str # HH:MM:SS format
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
links: Dict[str, List[str]] # session_id -> list of linked sessions
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

        """

Content Version Manager for AI Transcription & Knowledge Management Application

Handles the creation and management of different content versions:

- Original transcription
- Cleaned version (grammar fixes, filler word removal)
- Summary version(s)

This module provides seamless switching between versions while preserving timestamps
and enabling the second-brain architecture.
"""

import re
import json
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum

class VersionType(Enum):
"""Supported content version types"""
ORIGINAL = "original"
CLEANED = "cleaned"
SUMMARY_BRIEF = "summary_brief"
SUMMARY_DETAILED = "summary_detailed"
SUMMARY_KEYPOINTS = "summary_keypoints"

class CleaningLevel(Enum):
"""Different levels of content cleaning"""
LIGHT = "light" # Basic filler word removal
MODERATE = "moderate" # Filler words + basic grammar fixes
HEAVY = "heavy" # Full grammar correction + restructuring

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

class ContentVersionManager:
"""
Manages multiple versions of transcribed content with timestamp preservation.

    Features:
    - Version creation and switching
    - Timestamp preservation across versions
    - Content cleaning and summarization
    - Metadata tracking and analytics
    """

    def __init__(self):
        self.versions: Dict[VersionType, ContentVersion] = {}
        self.current_version: VersionType = VersionType.ORIGINAL
        self.source_metadata: Dict[str, Any] = {}

        # Filler words and patterns for cleaning
        self.filler_patterns = [
            r'\b(um|uh|er|ah|like|you know|sort of|kind of)\b',
            r'\b(basically|actually|literally|obviously)\b',
            r'\[.*?\]',  # Remove bracketed content like [inaudible]
            r'\(.*?\)',  # Remove parenthetical content
        ]

        # Grammar correction patterns
        self.grammar_patterns = [
            (r'\bi\b', 'I'),  # Capitalize standalone 'i'
            (r'(\w+)\s+\1\b', r'\1'),  # Remove word repetitions
            (r'\s+', ' '),  # Normalize whitespace
            (r'([.!?])\s*([a-z])', r'\1 \2'.upper()),  # Capitalize after punctuation
        ]

    def add_original_version(self, segments: List[TimestampedSegment], metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add the original transcription version"""
        full_text = ' '.join([seg.text for seg in segments])

        version = ContentVersion(
            version_type=VersionType.ORIGINAL,
            segments=segments,
            full_text=full_text,
            metadata=metadata or {},
            created_at=datetime.now(),
            word_count=len(full_text.split())
        )

        self.versions[VersionType.ORIGINAL] = version
        self.current_version = VersionType.ORIGINAL

        # Store source metadata
        if metadata:
            self.source_metadata.update(metadata)

    def create_cleaned_version(self, cleaning_level: CleaningLevel = CleaningLevel.MODERATE) -> ContentVersion:
        """
        Create a cleaned version of the content

        Args:
            cleaning_level: Level of cleaning to apply

        Returns:
            ContentVersion: The cleaned version
        """
        if VersionType.ORIGINAL not in self.versions:
            raise ValueError("Original version must exist before creating cleaned version")

        start_time = datetime.now()
        original = self.versions[VersionType.ORIGINAL]

        # Clean each segment
        cleaned_segments = []
        for segment in original.segments:
            cleaned_text = self._clean_text(segment.text, cleaning_level)

            cleaned_segment = TimestampedSegment(
                start_time=segment.start_time,
                end_time=segment.end_time,
                text=cleaned_text,
                speaker=segment.speaker,
                confidence=segment.confidence,
                version_metadata={'cleaning_level': cleaning_level.value}
            )
            cleaned_segments.append(cleaned_segment)

        full_text = ' '.join([seg.text for seg in cleaned_segments if seg.text.strip()])

        cleaned_version = ContentVersion(
            version_type=VersionType.CLEANED,
            segments=cleaned_segments,
            full_text=full_text,
            metadata={
                'cleaning_level': cleaning_level.value,
                'original_word_count': original.word_count,
                'words_removed': original.word_count - len(full_text.split())
            },
            created_at=datetime.now(),
            word_count=len(full_text.split()),
            processing_time=(datetime.now() - start_time).total_seconds()
        )

        self.versions[VersionType.CLEANED] = cleaned_version
        return cleaned_version

    def create_summary(self, summary_type: VersionType, max_sentences: Optional[int] = None) -> ContentVersion:
        """
        Create a summary version of the content

        Args:
            summary_type: Type of summary to create
            max_sentences: Maximum number of sentences (if applicable)

        Returns:
            ContentVersion: The summary version
        """
        if summary_type not in [VersionType.SUMMARY_BRIEF, VersionType.SUMMARY_DETAILED, VersionType.SUMMARY_KEYPOINTS]:
            raise ValueError(f"Invalid summary type: {summary_type}")

        # Use cleaned version if available, otherwise original
        source_version = self.versions.get(VersionType.CLEANED) or self.versions.get(VersionType.ORIGINAL)
        if not source_version:
            raise ValueError("No source version available for summarization")

        start_time = datetime.now()

        # Create summary based on type
        summary_text, summary_segments = self._create_summary_content(source_version, summary_type, max_sentences)

        summary_version = ContentVersion(
            version_type=summary_type,
            segments=summary_segments,
            full_text=summary_text,
            metadata={
                'source_version': source_version.version_type.value,
                'compression_ratio': len(summary_text) / len(source_version.full_text),
                'original_segments': len(source_version.segments),
                'summary_segments': len(summary_segments)
            },
            created_at=datetime.now(),
            word_count=len(summary_text.split()),
            processing_time=(datetime.now() - start_time).total_seconds()
        )

        self.versions[summary_type] = summary_version
        return summary_version

    def switch_version(self, version_type: VersionType) -> ContentVersion:
        """
        Switch to a specific version

        Args:
            version_type: Version to switch to

        Returns:
            ContentVersion: The requested version
        """
        if version_type not in self.versions:
            raise ValueError(f"Version {version_type.value} does not exist")

        self.current_version = version_type
        return self.versions[version_type]

    def get_current_version(self) -> ContentVersion:
        """Get the currently active version"""
        return self.versions[self.current_version]

    def get_available_versions(self) -> List[VersionType]:
        """Get list of available versions"""
        return list(self.versions.keys())

    def find_segment_at_timestamp(self, timestamp: float, version_type: Optional[VersionType] = None) -> Optional[TimestampedSegment]:
        """
        Find the segment containing a specific timestamp

        Args:
            timestamp: Time in seconds
            version_type: Version to search in (current if None)

        Returns:
            TimestampedSegment or None if not found
        """
        version = self.versions.get(version_type or self.current_version)
        if not version:
            return None

        for segment in version.segments:
            if segment.start_time <= timestamp <= segment.end_time:
                return segment

        return None

    def get_version_analytics(self) -> Dict[str, Any]:
        """Get analytics about all versions"""
        analytics = {
            'total_versions': len(self.versions),
            'available_versions': [v.value for v in self.versions.keys()],
            'current_version': self.current_version.value,
            'source_metadata': self.source_metadata
        }

        # Version-specific analytics
        for version_type, version in self.versions.items():
            key = f"{version_type.value}_stats"
            analytics[key] = {
                'word_count': version.word_count,
                'segment_count': len(version.segments),
                'duration': version.segments[-1].end_time if version.segments else 0,
                'created_at': version.created_at.isoformat(),
                'processing_time': version.processing_time
            }

        return analytics

    def export_version(self, version_type: VersionType, format_type: str = 'json') -> str:
        """
        Export a specific version in various formats

        Args:
            version_type: Version to export
            format_type: Export format ('json', 'srt', 'vtt', 'txt')

        Returns:
            Formatted string
        """
        if version_type not in self.versions:
            raise ValueError(f"Version {version_type.value} does not exist")

        version = self.versions[version_type]

        if format_type == 'json':
            return self._export_json(version)
        elif format_type == 'srt':
            return self._export_srt(version)
        elif format_type == 'vtt':
            return self._export_vtt(version)
        elif format_type == 'txt':
            return version.full_text
        else:
            raise ValueError(f"Unsupported export format: {format_type}")

    def _clean_text(self, text: str, cleaning_level: CleaningLevel) -> str:
        """Apply cleaning based on level"""
        if cleaning_level == CleaningLevel.LIGHT:
            # Only remove basic filler words
            for pattern in self.filler_patterns[:2]:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)

        elif cleaning_level == CleaningLevel.MODERATE:
            # Remove filler words and basic cleanup
            for pattern in self.filler_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)

            # Apply basic grammar fixes
            for find_pattern, replace_pattern in self.grammar_patterns[:2]:
                text = re.sub(find_pattern, replace_pattern, text)

        elif cleaning_level == CleaningLevel.HEAVY:
            # Full cleaning treatment
            for pattern in self.filler_patterns:
                text = re.sub(pattern, '', text, flags=re.IGNORECASE)

            # Apply all grammar fixes
            for find_pattern, replace_pattern in self.grammar_patterns:
                text = re.sub(find_pattern, replace_pattern, text)

        # Clean up extra whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text

    def _create_summary_content(self, source_version: ContentVersion, summary_type: VersionType, max_sentences: Optional[int]) -> Tuple[str, List[TimestampedSegment]]:
        """Create summary content based on type"""
        # This is a basic implementation - in production, you'd use AI for better summarization
        sentences = self._split_into_sentences(source_version.full_text)

        if summary_type == VersionType.SUMMARY_BRIEF:
            # Take first and last sentences, plus key middle points
            summary_sentences = self._extract_key_sentences(sentences, 3)
        elif summary_type == VersionType.SUMMARY_DETAILED:
            # More comprehensive summary
            summary_sentences = self._extract_key_sentences(sentences, min(10, len(sentences) // 3))
        elif summary_type == VersionType.SUMMARY_KEYPOINTS:
            # Extract key points as bullet points
            summary_sentences = self._extract_key_points(sentences)

        if max_sentences:
            summary_sentences = summary_sentences[:max_sentences]

        summary_text = ' '.join(summary_sentences)

        # Create summary segments with preserved timestamps
        summary_segments = self._create_summary_segments(source_version.segments, summary_sentences)

        return summary_text, summary_segments

    def _split_into_sentences(self, text: str) -> List[str]:
        """Split text into sentences"""
        import re
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]

    def _extract_key_sentences(self, sentences: List[str], count: int) -> List[str]:
        """Extract key sentences (basic implementation)"""
        if len(sentences) <= count:
            return sentences

        # Simple approach: take sentences at regular intervals
        step = len(sentences) // count
        key_sentences = []

        for i in range(0, len(sentences), step):
            if len(key_sentences) < count:
                key_sentences.append(sentences[i])

        return key_sentences

    def _extract_key_points(self, sentences: List[str]) -> List[str]:
        """Extract key points as structured bullets"""
        # Basic implementation - look for sentences with key indicators
        key_indicators = ['first', 'second', 'third', 'important', 'key', 'main', 'primary']
        key_sentences = []

        for sentence in sentences:
            if any(indicator in sentence.lower() for indicator in key_indicators):
                key_sentences.append(f"• {sentence}")
            elif len(sentence.split()) > 10:  # Longer sentences often contain more info
                key_sentences.append(f"• {sentence}")

        return key_sentences[:5]  # Limit to 5 key points

    def _create_summary_segments(self, original_segments: List[TimestampedSegment], summary_sentences: List[str]) -> List[TimestampedSegment]:
        """Create segments for summary with preserved timestamps"""
        # Simple approach: distribute summary sentences across original timeline
        if not original_segments:
            return []

        summary_segments = []
        total_duration = original_segments[-1].end_time
        segment_duration = total_duration / len(summary_sentences)

        for i, sentence in enumerate(summary_sentences):
            start_time = i * segment_duration
            end_time = (i + 1) * segment_duration

            segment = TimestampedSegment(
                start_time=start_time,
                end_time=end_time,
                text=sentence,
                version_metadata={'summary_index': i}
            )
            summary_segments.append(segment)

        return summary_segments

    def _export_json(self, version: ContentVersion) -> str:
        """Export version as JSON"""
        data = {
            'version_type': version.version_type.value,
            'full_text': version.full_text,
            'word_count': version.word_count,
            'created_at': version.created_at.isoformat(),
            'metadata': version.metadata,
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
        return json.dumps(data, indent=2)

    def _export_srt(self, version: ContentVersion) -> str:
        """Export version as SRT subtitle format"""
        srt_content = []

        for i, segment in enumerate(version.segments, 1):
            start_time = self._seconds_to_srt_time(segment.start_time)
            end_time = self._seconds_to_srt_time(segment.end_time)

            srt_content.append(f"{i}")
            srt_content.append(f"{start_time} --> {end_time}")
            srt_content.append(segment.text)
            srt_content.append("")  # Blank line between subtitles

        return '\n'.join(srt_content)

    def _export_vtt(self, version: ContentVersion) -> str:
        """Export version as WebVTT format"""
        vtt_content = ["WEBVTT", ""]

        for segment in version.segments:
            start_time = self._seconds_to_vtt_time(segment.start_time)
            end_time = self._seconds_to_vtt_time(segment.end_time)

            vtt_content.append(f"{start_time} --> {end_time}")
            vtt_content.append(segment.text)
            vtt_content.append("")

        return '\n'.join(vtt_content)

    def _seconds_to_srt_time(self, seconds: float) -> str:
        """Convert seconds to SRT time format (HH:MM:SS,mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"

    def _seconds_to_vtt_time(self, seconds: float) -> str:
        """Convert seconds to WebVTT time format (HH:MM:SS.mmm)"""
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        milliseconds = int((seconds % 1) * 1000)

        return f"{hours:02d}:{minutes:02d}:{secs:02d}.{milliseconds:03d}"

# Example usage and testing

if **name** == "**main**": # Example usage
manager = ContentVersionManager()

    # Create sample segments
    sample_segments = [
        TimestampedSegment(0.0, 5.0, "Um, hello everyone, this is like a test recording, you know."),
        TimestampedSegment(5.0, 10.0, "We're going to, uh, discuss some important topics today."),
        TimestampedSegment(10.0, 15.0, "First, we need to understand the basics of the system."),
        TimestampedSegment(15.0, 20.0, "Actually, this is really important for everyone to understand.")
    ]

    # Add original version
    manager.add_original_version(sample_segments, {'source': 'test_recording.wav'})

    # Create cleaned version
    cleaned = manager.create_cleaned_version(CleaningLevel.MODERATE)
    print(f"Cleaned version: {cleaned.full_text}")

    # Create summary
    summary = manager.create_summary(VersionType.SUMMARY_BRIEF)
    print(f"Summary: {summary.full_text}")

    # Switch versions
    manager.switch_version(VersionType.CLEANED)
    print(f"Current version: {manager.current_version}")

    # Get analytics
    analytics = manager.get_version_analytics()
    print(f"Analytics: {json.dumps(analytics, indent=2)}")

    """

Privacy Manager for AI Transcription & Knowledge Management Application

Provides comprehensive privacy control and data sharing transparency:

- Configurable privacy modes (private, selective, open)
- AI provider permissions management
- Real-time data usage tracking and logging
- Content anonymization and sanitization
- GDPR/CCPA compliance features

This module ensures users have complete control over what data is shared
with which AI providers and when.
"""

# backend/privacy/privacy_manager.py

import hashlib
import json
import sqlite3
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

# Configure logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(**name**)

class PrivacyMode(Enum):
PRIVATE = "private" # No AI processing, local only
SELECTIVE = "selective" # User controls what goes to AI
OPEN = "open" # All content can be processed by AI

class DataSensitivity(Enum):
PUBLIC = "public" # Can be shared freely
PERSONAL = "personal" # Contains personal information
CONFIDENTIAL = "confidential" # Sensitive business/private data
RESTRICTED = "restricted" # Must not be shared externally

class AIProvider(Enum):
OPENAI = "openai"
ANTHROPIC = "anthropic"
GOOGLE = "google"
HUGGINGFACE = "huggingface"
OPENROUTER = "openrouter"
LOCAL = "local"

@dataclass
class AIUsageLog:
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
mode: PrivacyMode
allowed_providers: List[AIProvider]
auto_anonymize: bool
require_approval: bool
max_retention_days: int
sensitive_patterns: List[str]
blocked_content_types: List[str]

class PrivacyManager:
def **init**(self, db*path: str = "privacy_data.db"):
self.db_path = db_path
self.privacy_mode = PrivacyMode.PRIVATE
self.settings = PrivacySettings(
mode=PrivacyMode.PRIVATE,
allowed_providers=[AIProvider.LOCAL],
auto_anonymize=True,
require_approval=True,
max_retention_days=30,
sensitive_patterns=[
r'\b\d{3}-\d{2}-\d{4}\b', # SSN
r'\b\d{4}-\d{4}-\d{4}-\d{4}\b', # Credit card
r'\b[A-Za-z0-9.*%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', # Email
r'\b\d{3}-\d{3}-\d{4}\b', # Phone number
],
blocked_content_types=["financial", "medical", "legal"]
)
self.usage_log: List[AIUsageLog] = []
self.\_init_database()

    def _init_database(self):
        """Initialize SQLite database for privacy tracking"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Create privacy settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS privacy_settings (
                    id INTEGER PRIMARY KEY,
                    mode TEXT NOT NULL,
                    settings_json TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create AI usage log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    timestamp TIMESTAMP NOT NULL,
                    data_sent_size INTEGER NOT NULL,
                    anonymized BOOLEAN NOT NULL,
                    user_approved BOOLEAN NOT NULL,
                    retention_days INTEGER NOT NULL,
                    expires_at TIMESTAMP NOT NULL
                )
            ''')

            # Create data inventory table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS data_inventory (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_hash TEXT UNIQUE NOT NULL,
                    content_type TEXT NOT NULL,
                    sensitivity_level TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    access_count INTEGER DEFAULT 1,
                    location TEXT NOT NULL,
                    metadata_json TEXT
                )
            ''')

            conn.commit()
            conn.close()
            logger.info("Privacy database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize privacy database: {e}")
            raise

    def set_privacy_mode(self, mode: PrivacyMode) -> bool:
        """Set the global privacy mode"""
        try:
            self.privacy_mode = mode
            self.settings.mode = mode

            # Update default settings based on mode
            if mode == PrivacyMode.PRIVATE:
                self.settings.allowed_providers = [AIProvider.LOCAL]
                self.settings.require_approval = True
                self.settings.auto_anonymize = True
            elif mode == PrivacyMode.SELECTIVE:
                self.settings.require_approval = True
                self.settings.auto_anonymize = True
            elif mode == PrivacyMode.OPEN:
                self.settings.allowed_providers = list(AIProvider)
                self.settings.require_approval = False
                self.settings.auto_anonymize = False

            self._save_settings()
            logger.info(f"Privacy mode set to {mode.value}")
            return True
        except Exception as e:
            logger.error(f"Failed to set privacy mode: {e}")
            return False

    def check_ai_permission(self, content: str, provider: AIProvider, task_type: str) -> Tuple[bool, str]:
        """Check if content can be sent to specific AI provider"""
        try:
            # Check if provider is allowed
            if provider not in self.settings.allowed_providers:
                return False, f"Provider {provider.value} not in allowed list"

            # Check privacy mode restrictions
            if self.privacy_mode == PrivacyMode.PRIVATE and provider != AIProvider.LOCAL:
                return False, "Private mode only allows local AI processing"

            # Check content sensitivity
            sensitivity = self._analyze_content_sensitivity(content)
            if sensitivity in [DataSensitivity.CONFIDENTIAL, DataSensitivity.RESTRICTED]:
                if provider != AIProvider.LOCAL:
                    return False, f"Content sensitivity level {sensitivity.value} requires local processing only"

            # Check for blocked content types
            content_type = self._classify_content_type(content)
            if content_type in self.settings.blocked_content_types:
                return False, f"Content type {content_type} is blocked from AI processing"

            # Check if user approval is required
            if self.settings.require_approval:
                # In a real implementation, this would prompt the user
                # For now, we'll assume approval for non-sensitive content
                if sensitivity not in [DataSensitivity.CONFIDENTIAL, DataSensitivity.RESTRICTED]:
                    return True, "Permission granted with user approval simulation"
                else:
                    return False, "User approval required for sensitive content"

            return True, "Permission granted"

        except Exception as e:
            logger.error(f"Error checking AI permission: {e}")
            return False, f"Error during permission check: {e}"

    def log_ai_usage(self, content: str, provider: AIProvider, task_type: str,
                     data_sent_size: int, anonymized: bool = False, user_approved: bool = False) -> str:
        """Log AI usage with transparent tracking"""
        try:
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            timestamp = datetime.now()

            usage_log = AIUsageLog(
                content_hash=content_hash,
                provider=provider,
                task_type=task_type,
                timestamp=timestamp,
                data_sent_size=data_sent_size,
                anonymized=anonymized,
                user_approved=user_approved,
                retention_days=self.settings.max_retention_days
            )

            self.usage_log.append(usage_log)

            # Save to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            expires_at = timestamp + timedelta(days=self.settings.max_retention_days)

            cursor.execute('''
                INSERT INTO ai_usage_log
                (content_hash, provider, task_type, timestamp, data_sent_size,
                 anonymized, user_approved, retention_days, expires_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (content_hash, provider.value, task_type, timestamp,
                  data_sent_size, anonymized, user_approved,
                  self.settings.max_retention_days, expires_at))

            conn.commit()
            conn.close()

            logger.info(f"AI usage logged: {provider.value} - {task_type} - {len(content)} chars")
            return content_hash

        except Exception as e:
            logger.error(f"Failed to log AI usage: {e}")
            return ""

    def anonymize_content(self, text: str, anonymization_level: str = "standard") -> Tuple[str, Dict]:
        """Remove or replace identifying information from content"""
        try:
            anonymized_text = text
            replacements = {}

            if anonymization_level in ["standard", "aggressive"]:
                # Replace sensitive patterns
                for i, pattern in enumerate(self.settings.sensitive_patterns):
                    matches = re.findall(pattern, anonymized_text)
                    for match in matches:
                        placeholder = f"[REDACTED_{i}]"
                        replacements[match] = placeholder
                        anonymized_text = anonymized_text.replace(match, placeholder)

                # Replace names (basic implementation)
                name_patterns = [
                    r'\b[A-Z][a-z]+ [A-Z][a-z]+\b',  # First Last
                    r'\bMr\. [A-Z][a-z]+\b',         # Mr. Lastname
                    r'\bMs\. [A-Z][a-z]+\b',         # Ms. Lastname
                    r'\bDr\. [A-Z][a-z]+\b',         # Dr. Lastname
                ]

                for pattern in name_patterns:
                    matches = re.findall(pattern, anonymized_text)
                    for match in matches:
                        if match not in replacements:
                            placeholder = "[NAME]"
                            replacements[match] = placeholder
                            anonymized_text = anonymized_text.replace(match, placeholder)

            if anonymization_level == "aggressive":
                # Additional aggressive anonymization
                # Replace locations, organizations, etc.
                location_patterns = [
                    r'\b[A-Z][a-z]+ [A-Z][a-z]+ (Street|St|Avenue|Ave|Road|Rd|Boulevard|Blvd)\b',
                    r'\b[A-Z][a-z]+, [A-Z]{2}\b',  # City, ST
                ]

                for pattern in location_patterns:
                    matches = re.findall(pattern, anonymized_text)
                    for match in matches:
                        if match not in replacements:
                            placeholder = "[LOCATION]"
                            replacements[match] = placeholder
                            anonymized_text = anonymized_text.replace(match, placeholder)

            logger.info(f"Content anonymized: {len(replacements)} replacements made")
            return anonymized_text, replacements

        except Exception as e:
            logger.error(f"Failed to anonymize content: {e}")
            return text, {}

    def get_privacy_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive privacy dashboard information"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Get usage statistics
            cursor.execute('''
                SELECT provider, COUNT(*), SUM(data_sent_size),
                       AVG(anonymized), COUNT(CASE WHEN user_approved THEN 1 END)
                FROM ai_usage_log
                WHERE timestamp >= datetime('now', '-30 days')
                GROUP BY provider
            ''')

            usage_stats = []
            for row in cursor.fetchall():
                usage_stats.append({
                    'provider': row[0],
                    'requests': row[1],
                    'total_data_sent': row[2],
                    'anonymization_rate': row[3],
                    'approved_requests': row[4]
                })

            # Get data inventory summary
            cursor.execute('''
                SELECT sensitivity_level, COUNT(*), SUM(access_count)
                FROM data_inventory
                GROUP BY sensitivity_level
            ''')

            data_inventory = []
            for row in cursor.fetchall():
                data_inventory.append({
                    'sensitivity': row[0],
                    'items': row[1],
                    'total_accesses': row[2]
                })

            conn.close()

            dashboard_data = {
                'privacy_mode': self.privacy_mode.value,
                'settings': asdict(self.settings),
                'usage_statistics': usage_stats,
                'data_inventory': data_inventory,
                'recent_activity': self._get_recent_activity(),
                'privacy_score': self._calculate_privacy_score(),
                'recommendations': self._get_privacy_recommendations()
            }

            return dashboard_data

        except Exception as e:
            logger.error(f"Failed to get privacy dashboard data: {e}")
            return {}

    def cleanup_expired_data(self) -> int:
        """Clean up expired data according to retention policies"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Remove expired AI usage logs
            cursor.execute('''
                DELETE FROM ai_usage_log
                WHERE expires_at < datetime('now')
            ''')

            expired_logs = cursor.rowcount

            # Remove old data inventory entries (older than max retention)
            cursor.execute('''
                DELETE FROM data_inventory
                WHERE created_at < datetime('now', '-' || ? || ' days')
            ''', (self.settings.max_retention_days,))

            expired_inventory = cursor.rowcount

            conn.commit()
            conn.close()

            total_cleaned = expired_logs + expired_inventory
            logger.info(f"Cleaned up {total_cleaned} expired data records")
            return total_cleaned

        except Exception as e:
            logger.error(f"Failed to cleanup expired data: {e}")
            return 0

    def export_privacy_data(self, format: str = "json") -> str:
        """Export user's privacy data for transparency/GDPR compliance"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Export all privacy-related data
            cursor.execute('SELECT * FROM privacy_settings')
            settings_data = cursor.fetchall()

            cursor.execute('SELECT * FROM ai_usage_log')
            usage_data = cursor.fetchall()

            cursor.execute('SELECT * FROM data_inventory')
            inventory_data = cursor.fetchall()

            conn.close()

            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'privacy_settings': settings_data,
                'ai_usage_log': usage_data,
                'data_inventory': inventory_data,
                'current_settings': asdict(self.settings)
            }

            if format.lower() == "json":
                return json.dumps(export_data, indent=2, default=str)
            else:
                # Could implement other formats (CSV, XML, etc.)
                return json.dumps(export_data, indent=2, default=str)

        except Exception as e:
            logger.error(f"Failed to export privacy data: {e}")
            return "{}"

    def _analyze_content_sensitivity(self, content: str) -> DataSensitivity:
        """Analyze content to determine sensitivity level"""
        try:
            content_lower = content.lower()

            # Check for highly sensitive patterns
            sensitive_keywords = [
                'confidential', 'classified', 'secret', 'private',
                'medical', 'health', 'diagnosis', 'treatment',
                'financial', 'bank', 'account', 'salary', 'income',
                'legal', 'lawsuit', 'attorney', 'court'
            ]

            # Check for personal information patterns
            has_sensitive_patterns = any(re.search(pattern, content) for pattern in self.settings.sensitive_patterns)
            has_sensitive_keywords = any(keyword in content_lower for keyword in sensitive_keywords)

            if has_sensitive_patterns and has_sensitive_keywords:
                return DataSensitivity.RESTRICTED
            elif has_sensitive_patterns or has_sensitive_keywords:
                return DataSensitivity.CONFIDENTIAL
            elif any(word in content_lower for word in ['personal', 'private', 'individual']):
                return DataSensitivity.PERSONAL
            else:
                return DataSensitivity.PUBLIC

        except Exception as e:
            logger.error(f"Failed to analyze content sensitivity: {e}")
            return DataSensitivity.CONFIDENTIAL  # Default to most restrictive

    def _classify_content_type(self, content: str) -> str:
        """Classify content into categories"""
        try:
            content_lower = content.lower()

            if any(word in content_lower for word in ['medical', 'health', 'doctor', 'diagnosis']):
                return 'medical'
            elif any(word in content_lower for word in ['financial', 'bank', 'money', 'investment']):
                return 'financial'
            elif any(word in content_lower for word in ['legal', 'law', 'court', 'attorney']):
                return 'legal'
            elif any(word in content_lower for word in ['business', 'company', 'corporate']):
                return 'business'
            else:
                return 'general'

        except Exception as e:
            logger.error(f"Failed to classify content type: {e}")
            return 'unknown'

    def _save_settings(self):
        """Save current settings to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            settings_json = json.dumps(asdict(self.settings), default=str)

            cursor.execute('''
                INSERT OR REPLACE INTO privacy_settings (id, mode, settings_json, updated_at)
                VALUES (1, ?, ?, datetime('now'))
            ''', (self.privacy_mode.value, settings_json))

            conn.commit()
            conn.close()

        except Exception as e:
            logger.error(f"Failed to save settings: {e}")

    def _get_recent_activity(self) -> List[Dict]:
        """Get recent privacy-related activity"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                SELECT provider, task_type, timestamp, anonymized, user_approved
                FROM ai_usage_log
                WHERE timestamp >= datetime('now', '-7 days')
                ORDER BY timestamp DESC
                LIMIT 20
            ''')

            activity = []
            for row in cursor.fetchall():
                activity.append({
                    'provider': row[0],
                    'task_type': row[1],
                    'timestamp': row[2],
                    'anonymized': bool(row[3]),
                    'user_approved': bool(row[4])
                })

            conn.close()
            return activity

        except Exception as e:
            logger.error(f"Failed to get recent activity: {e}")
            return []

    def _calculate_privacy_score(self) -> int:
        """Calculate a privacy score (0-100) based on current settings and usage"""
        try:
            score = 0

            # Base score from privacy mode
            if self.privacy_mode == PrivacyMode.PRIVATE:
                score += 40
            elif self.privacy_mode == PrivacyMode.SELECTIVE:
                score += 25
            else:
                score += 10

            # Score from settings
            if self.settings.auto_anonymize:
                score += 15
            if self.settings.require_approval:
                score += 15
            if len(self.settings.allowed_providers) == 1 and AIProvider.LOCAL in self.settings.allowed_providers:
                score += 15
            elif len(self.settings.allowed_providers) <= 2:
                score += 10

            # Score from retention policy
            if self.settings.max_retention_days <= 30:
                score += 10
            elif self.settings.max_retention_days <= 90:
                score += 5

            # Score from recent usage patterns
            recent_local_usage = len([log for log in self.usage_log[-50:] if log.provider == AIProvider.LOCAL])
            if recent_local_usage > 0:
                score += min(5, recent_local_usage)

            return min(100, score)

        except Exception as e:
            logger.error(f"Failed to calculate privacy score: {e}")
            return 50

    def _get_privacy_recommendations(self) -> List[str]:
        """Get personalized privacy recommendations"""
        recommendations = []

        try:
            if self.privacy_mode != PrivacyMode.PRIVATE:
                recommendations.append("Consider switching to Private mode for maximum privacy protection")

            if not self.settings.auto_anonymize:
                recommendations.append("Enable auto-anonymization to protect sensitive information")

            if self.settings.max_retention_days > 30:
                recommendations.append("Reduce data retention period to 30 days or less")

            if len(self.settings.allowed_providers) > 3:
                recommendations.append("Limit the number of allowed AI providers to reduce data exposure")

            # Check recent usage patterns
            external_usage = len([log for log in self.usage_log[-20:] if log.provider != AIProvider.LOCAL])
            if external_usage > 10:
                recommendations.append("High external AI usage detected - consider using local models more frequently")

            return recommendations

        except Exception as e:
            logger.error(f"Failed to generate recommendations: {e}")
            return ["Enable privacy monitoring for personalized recommendations"]

            """

Universal Input Handler for PICO Transcription App
Handles all audio input sources: local files, live recording, YouTube, podcasts
"""

import os
import tempfile
import threading
import time
from typing import Optional, Dict, List, Callable
from pathlib import Path
import logging

# Core dependencies

import yt_dlp
import feedparser
import librosa
import soundfile as sf
import pyaudio
from pydub import AudioSegment
from urllib.parse import urlparse

class UniversalInputHandler:
"""
Handles all types of audio input for the transcription system.
Supports local files, live recording, YouTube videos, and podcast feeds.
"""

    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.gettempdir()
        self.audio_formats = {'.mp3', '.wav', '.flac', '.ogg', '.m4a', '.aac', '.wma'}
        self.video_formats = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}

        # Audio recording settings
        self.sample_rate = 16000  # Whisper's preferred sample rate
        self.channels = 1
        self.chunk_size = 1024
        self.format = pyaudio.paInt16

        # Initialize PyAudio for live recording
        self.audio_interface = pyaudio.PyAudio()
        self.recording_thread = None
        self.is_recording = False

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

    def process_input(self, source: str, callback: Optional[Callable] = None) -> Dict:
        """
        Universal entry point for all input types.
        Automatically detects the type of input and processes accordingly.

        Args:
            source: File path, URL, or RSS feed URL
            callback: Optional callback for progress updates

        Returns:
            Dict with processed audio info and file path
        """
        try:
            if self._is_url(source):
                if 'youtube.com' in source or 'youtu.be' in source:
                    return self.process_youtube_url(source, callback)
                elif self._is_rss_feed(source):
                    return self.process_podcast_feed(source, callback)
                else:
                    return self.process_web_audio(source, callback)
            else:
                return self.process_local_file(source, callback)

        except Exception as e:
            self.logger.error(f"Error processing input {source}: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_youtube_url(self, url: str, callback: Optional[Callable] = None) -> Dict:
        """
        Extract and process audio from YouTube videos.

        Args:
            url: YouTube video URL
            callback: Progress callback function

        Returns:
            Dict with success status, audio file path, and metadata
        """
        try:
            self.logger.info(f"Processing YouTube URL: {url}")

            # Configure yt-dlp options
            output_path = os.path.join(self.temp_dir, f"youtube_audio_{int(time.time())}.wav")

            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_path.replace('.wav', '.%(ext)s'),
                'extractaudio': True,
                'audioformat': 'wav',
                'prefer_ffmpeg': True,
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': 'wav',
                    'preferredquality': '192',
                }],
            }

            # Add progress hook if callback provided
            if callback:
                def progress_hook(d):
                    if d['status'] == 'downloading':
                        percent = d.get('_percent_str', 'N/A')
                        callback(f"Downloading: {percent}")
                    elif d['status'] == 'finished':
                        callback("Download complete, processing audio...")

                ydl_opts['progress_hooks'] = [progress_hook]

            # Download and extract audio
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=True)
                title = info.get('title', 'Unknown')
                duration = info.get('duration', 0)

                # Find the actual output file
                base_path = output_path.replace('.wav', '')
                for ext in ['.wav', '.m4a', '.webm', '.mp3']:
                    potential_path = base_path + ext
                    if os.path.exists(potential_path):
                        if ext != '.wav':
                            # Convert to WAV if needed
                            output_path = self._convert_to_wav(potential_path)
                            os.remove(potential_path)
                        else:
                            output_path = potential_path
                        break

                # Normalize audio for Whisper
                normalized_path = self._normalize_audio(output_path)

                return {
                    'success': True,
                    'audio_path': normalized_path,
                    'title': title,
                    'duration': duration,
                    'source_type': 'youtube',
                    'source_url': url
                }

        except Exception as e:
            self.logger.error(f"YouTube processing error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_podcast_feed(self, rss_url: str, callback: Optional[Callable] = None, episode_limit: int = 5) -> List[Dict]:
        """
        Process podcast RSS feed and return available episodes.

        Args:
            rss_url: RSS feed URL
            callback: Progress callback function
            episode_limit: Maximum number of episodes to process

        Returns:
            List of episode dictionaries
        """
        try:
            self.logger.info(f"Processing podcast feed: {rss_url}")

            # Parse RSS feed
            feed = feedparser.parse(rss_url)
            if not feed.entries:
                return {'success': False, 'error': 'No episodes found in feed'}

            episodes = []
            for i, entry in enumerate(feed.entries[:episode_limit]):
                if callback:
                    callback(f"Processing episode {i+1}/{min(episode_limit, len(feed.entries))}")

                # Find audio URL
                audio_url = None
                for link in entry.get('links', []):
                    if 'audio' in link.get('type', ''):
                        audio_url = link['href']
                        break

                if not audio_url and hasattr(entry, 'enclosures'):
                    for enclosure in entry.enclosures:
                        if 'audio' in enclosure.type:
                            audio_url = enclosure.href
                            break

                if audio_url:
                    episode_info = {
                        'title': entry.get('title', 'Unknown Episode'),
                        'description': entry.get('description', ''),
                        'published': entry.get('published', ''),
                        'audio_url': audio_url,
                        'source_type': 'podcast',
                        'source_feed': rss_url
                    }
                    episodes.append(episode_info)

            return {'success': True, 'episodes': episodes}

        except Exception as e:
            self.logger.error(f"Podcast feed processing error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def process_local_file(self, file_path: str, callback: Optional[Callable] = None) -> Dict:
        """
        Process local audio or video files.

        Args:
            file_path: Path to local file
            callback: Progress callback function

        Returns:
            Dict with processed audio info
        """
        try:
            if not os.path.exists(file_path):
                return {'success': False, 'error': 'File not found'}

            file_ext = Path(file_path).suffix.lower()
            self.logger.info(f"Processing local file: {file_path}")

            if callback:
                callback("Processing local file...")

            # Handle different file types
            if file_ext in self.audio_formats:
                # Direct audio file processing
                output_path = self._normalize_audio(file_path)
            elif file_ext in self.video_formats:
                # Extract audio from video
                output_path = self._extract_audio_from_video(file_path)
            else:
                return {'success': False, 'error': f'Unsupported file format: {file_ext}'}

            # Get file metadata
            duration = librosa.get_duration(filename=output_path)

            return {
                'success': True,
                'audio_path': output_path,
                'title': Path(file_path).stem,
                'duration': duration,
                'source_type': 'local_file',
                'source_path': file_path
            }

        except Exception as e:
            self.logger.error(f"Local file processing error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def start_live_recording(self, callback: Optional[Callable] = None, device_id: Optional[int] = None) -> Dict:
        """
        Start live audio recording from microphone.

        Args:
            callback: Callback for audio chunks (for real-time processing)
            device_id: Specific audio device ID (None for default)

        Returns:
            Dict with recording info
        """
        try:
            if self.is_recording:
                return {'success': False, 'error': 'Already recording'}

            self.is_recording = True
            output_path = os.path.join(self.temp_dir, f"live_recording_{int(time.time())}.wav")

            # Audio recording configuration
            stream = self.audio_interface.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=device_id,
                frames_per_buffer=self.chunk_size
            )

            frames = []

            def record_thread():
                self.logger.info("Started live recording")
                try:
                    while self.is_recording:
                        data = stream.read(self.chunk_size, exception_on_overflow=False)
                        frames.append(data)

                        # Call callback with chunk if provided
                        if callback:
                            callback(data)

                except Exception as e:
                    self.logger.error(f"Recording error: {str(e)}")
                finally:
                    stream.stop_stream()
                    stream.close()

                    # Save recording to file
                    if frames:
                        with sf.SoundFile(output_path, 'w',
                                        samplerate=self.sample_rate,
                                        channels=self.channels,
                                        format='WAV') as f:
                            audio_data = b''.join(frames)
                            f.write(audio_data)

            self.recording_thread = threading.Thread(target=record_thread)
            self.recording_thread.start()

            return {
                'success': True,
                'recording': True,
                'output_path': output_path,
                'source_type': 'live_recording'
            }

        except Exception as e:
            self.logger.error(f"Live recording error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def stop_live_recording(self) -> Dict:
        """Stop live recording and return the recorded file."""
        if not self.is_recording:
            return {'success': False, 'error': 'Not currently recording'}

        self.is_recording = False

        if self.recording_thread:
            self.recording_thread.join(timeout=5.0)

        self.logger.info("Stopped live recording")
        return {'success': True, 'recording': False}

    def get_available_devices(self) -> List[Dict]:
        """Get list of available audio input devices."""
        devices = []

        for i in range(self.audio_interface.get_device_count()):
            info = self.audio_interface.get_device_info_by_index(i)
            if info['maxInputChannels'] > 0:
                devices.append({
                    'id': i,
                    'name': info['name'],
                    'channels': info['maxInputChannels'],
                    'sample_rate': int(info['defaultSampleRate'])
                })

        return devices

    def _is_url(self, source: str) -> bool:
        """Check if source is a URL."""
        parsed = urlparse(source)
        return bool(parsed.scheme and parsed.netloc)

    def _is_rss_feed(self, url: str) -> bool:
        """Check if URL is likely an RSS feed."""
        try:
            feed = feedparser.parse(url)
            return bool(feed.entries)
        except:
            return False

    def _convert_to_wav(self, input_path: str) -> str:
        """Convert audio file to WAV format."""
        output_path = input_path.rsplit('.', 1)[0] + '.wav'

        audio = AudioSegment.from_file(input_path)
        audio.export(output_path, format='wav')

        return output_path

    def _normalize_audio(self, input_path: str) -> str:
        """Normalize audio for Whisper processing."""
        if input_path.endswith('_normalized.wav'):
            return input_path

        output_path = input_path.rsplit('.', 1)[0] + '_normalized.wav'

        # Load and resample to 16kHz mono
        y, sr = librosa.load(input_path, sr=self.sample_rate, mono=True)

        # Save normalized audio
        sf.write(output_path, y, self.sample_rate)

        return output_path

    def _extract_audio_from_video(self, video_path: str) -> str:
        """Extract audio from video file."""
        output_path = os.path.join(self.temp_dir, f"extracted_audio_{int(time.time())}.wav")

        # Use pydub to extract audio
        video = AudioSegment.from_file(video_path)
        video.export(output_path, format='wav')

        return self._normalize_audio(output_path)

    def process_web_audio(self, url: str, callback: Optional[Callable] = None) -> Dict:
        """Process direct audio URLs."""
        try:
            import requests

            if callback:
                callback("Downloading audio from URL...")

            response = requests.get(url, stream=True)
            response.raise_for_status()

            output_path = os.path.join(self.temp_dir, f"web_audio_{int(time.time())}")

            # Save file with appropriate extension
            content_type = response.headers.get('content-type', '')
            if 'audio/mpeg' in content_type:
                output_path += '.mp3'
            elif 'audio/wav' in content_type:
                output_path += '.wav'
            else:
                output_path += '.mp3'  # Default

            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            # Convert and normalize
            normalized_path = self._normalize_audio(output_path)
            os.remove(output_path)

            duration = librosa.get_duration(filename=normalized_path)

            return {
                'success': True,
                'audio_path': normalized_path,
                'title': 'Web Audio',
                'duration': duration,
                'source_type': 'web_audio',
                'source_url': url
            }

        except Exception as e:
            self.logger.error(f"Web audio processing error: {str(e)}")
            return {'success': False, 'error': str(e)}

    def cleanup_temp_files(self):
        """Clean up temporary audio files."""
        try:
            temp_files = [f for f in os.listdir(self.temp_dir)
                         if f.startswith(('youtube_audio_', 'extracted_audio_', 'live_recording_', 'web_audio_'))]

            for file in temp_files:
                file_path = os.path.join(self.temp_dir, file)
                if os.path.exists(file_path):
                    os.remove(file_path)

            self.logger.info(f"Cleaned up {len(temp_files)} temporary files")

        except Exception as e:
            self.logger.error(f"Cleanup error: {str(e)}")

    def __del__(self):
        """Cleanup resources."""
        if hasattr(self, 'is_recording') and self.is_recording:
            self.stop_live_recording()

        if hasattr(self, 'audio_interface'):
            self.audio_interface.terminate()

# Example usage and testing

if **name** == "**main**":
handler = UniversalInputHandler()

    def progress_callback(message):
        print(f"Progress: {message}")

    # Test with different input types

    # Example 1: YouTube video
    # result = handler.process_youtube_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ", progress_callback)
    # print("YouTube result:", result)

    # Example 2: Local file
    # result = handler.process_local_file("test_audio.mp3", progress_callback)
    # print("Local file result:", result)

    # Example 3: List available recording devices
    devices = handler.get_available_devices()
    print("Available devices:", devices)

    # Example 4: Universal input processing
    # result = handler.process_input("https://www.youtube.com/watch?v=example", progress_callback)
    # print("Universal processing result:", result)

    """

Core Transcription Engine for PICO Transcription App
Handles Whisper integration with precise timestamping and speaker diarization
"""

import os
import time
import logging
from typing import Optional, Dict, List, Callable, Tuple
from dataclasses import dataclass
from pathlib import Path
import json

# Core transcription dependencies

from faster_whisper import WhisperModel
import torch
import librosa
import numpy as np

# Speaker diarization (optional, install with: pip install pyannote-audio)

try:
from pyannote.audio import Pipeline
DIARIZATION_AVAILABLE = True
except ImportError:
DIARIZATION_AVAILABLE = False
print("Speaker diarization not available. Install with: pip install pyannote-audio")

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

class TranscriptionEngine:
"""
Core transcription engine with Whisper integration.
Supports multiple model sizes, GPU acceleration, and speaker diarization.
"""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        enable_diarization: bool = False,
        diarization_token: Optional[str] = None
    ):
        """
        Initialize the transcription engine.

        Args:
            model_size: Whisper model size (tiny, base, small, medium, large-v2, large-v3)
            device: Device to use (cpu, cuda, auto)
            compute_type: Compute type for faster-whisper (float16, int8, auto)
            enable_diarization: Whether to enable speaker diarization
            diarization_token: Hugging Face token for pyannote models
        """
        self.model_size = model_size
        self.device = self._get_optimal_device() if device == "auto" else device
        self.compute_type = self._get_optimal_compute_type() if compute_type == "auto" else compute_type
        self.enable_diarization = enable_diarization and DIARIZATION_AVAILABLE

        # Setup logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)

        # Initialize models
        self.whisper_model = None
        self.diarization_pipeline = None

        self._load_models(diarization_token)

        # Model performance stats
        self.stats = {
            'total_audio_processed': 0.0,
            'total_processing_time': 0.0,
            'average_speed_factor': 0.0,
            'transcriptions_completed': 0
        }

    def _get_optimal_device(self) -> str:
        """Determine the best device for processing."""
        if torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, 'mps') and torch.backends.mps.is_available():
            return "mps"  # Apple Silicon
        else:
            return "cpu"

    def _get_optimal_compute_type(self) -> str:
        """Determine the best compute type based on device."""
        if self.device == "cuda":
            # Check CUDA capability
            if torch.cuda.is_available():
                capability = torch.cuda.get_device_capability()
                if capability[0] >= 7:  # RTX series and newer
                    return "float16"
                else:
                    return "int8"
        elif self.device == "mps":
            return "float32"
        else:
            return "int8"

    def _load_models(self, diarization_token: Optional[str] = None):
        """Load Whisper and optionally diarization models."""
        try:
            self.logger.info(f"Loading Whisper model: {self.model_size} on {self.device}")

            self.whisper_model = WhisperModel(
                self.model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root="./models"
            )

            self.logger.info("Whisper model loaded successfully")

            # Load diarization model if enabled
            if self.enable_diarization:
                try:
                    self.logger.info("Loading speaker diarization model...")
                    self.diarization_pipeline = Pipeline.from_pretrained(
                        "pyannote/speaker-diarization-3.1",
                        use_auth_token=diarization_token
                    )

                    if self.device == "cuda":
                        self.diarization_pipeline.to(torch.device("cuda"))

                    self.logger.info("Diarization model loaded successfully")

                except Exception as e:
                    self.logger.warning(f"Failed to load diarization model: {str(e)}")
                    self.enable_diarization = False

        except Exception as e:
            self.logger.error(f"Model loading error: {str(e)}")
            raise

    def transcribe(
        self,
        audio_path: str,
        language: Optional[str] = None,
        progress_callback: Optional[Callable] = None,
        word_timestamps: bool = True,
        vad_filter: bool = True,
        beam_size: int = 5
    ) -> TranscriptionResult:
        """
        Transcribe audio file with precise timestamps and optional speaker diarization.

        Args:
            audio_path: Path to audio file
            language: Language code (auto-detect if None)
            progress_callback: Optional callback for progress updates
            word_timestamps: Whether to include word-level timestamps
            vad_filter: Whether to use voice activity detection
            beam_size: Beam search size for better quality

        Returns:
            TranscriptionResult object with all transcription data
        """
        start_time = time.time()

        try:
            if not os.path.exists(audio_path):
                raise FileNotFoundError(f"Audio file not found: {audio_path}")

            # Get audio duration
            duration = librosa.get_duration(filename=audio_path)
            self.logger.info(f"Transcribing {duration:.2f}s audio file: {audio_path}")

            if progress_callback:
                progress_callback("Starting transcription...")

            # Perform speaker diarization first if enabled
            speaker_info = None
            if self.enable_diarization:
                if progress_callback:
                    progress_callback("Analyzing speakers...")
                speaker_info = self._perform_diarization(audio_path)

            # Transcribe with Whisper
            if progress_callback:
                progress_callback("Transcribing audio...")

            segments, info = self.whisper_model.transcribe(
                audio_path,
                language=language,
                beam_size=beam_size,
                word_timestamps=word_timestamps,
                vad_filter=vad_filter,
                vad_parameters=dict(
                    min_silence_duration_ms=500,
                    speech_pad_ms=400
                )
            )

            # Process segments
            transcription_segments = []
            for i, segment in enumerate(segments):
                if progress_callback:
                    progress_callback(f"Processing segment {i+1}...")

                # Find speaker for this segment if diarization is available
                speaker = None
                if speaker_info:
                    speaker = self._assign_speaker_to_segment(
                        segment.start, segment.end, speaker_info
                    )

                # Process word-level timestamps if available
                words = None
                if hasattr(segment, 'words') and segment.words:
                    words = [
                        {
                            'word': word.word,
                            'start': word.start,
                            'end': word.end,
                            'confidence': getattr(word, 'probability', 0.0)
                        }
                        for word in segment.words
                    ]

                transcription_segments.append(TranscriptionSegment(
                    id=i,
                    text=segment.text.strip(),
                    start=segment.start,
                    end=segment.end,
                    confidence=getattr(segment, 'avg_logprob', 0.0),
                    speaker=speaker,
                    words=words
                ))

            # Calculate processing stats
            processing_time = time.time() - start_time
            speed_factor = duration / processing_time if processing_time > 0 else 0

            # Update stats
            self._update_stats(duration, processing_time)

            # Create result
            result = TranscriptionResult(
                segments=transcription_segments,
                language=info.language,
                duration=duration,
                processing_time=processing_time,
                model_used=self.model_size,
                source_info={
                    'file_path': audio_path,
                    'file_size': os.path.getsize(audio_path),
                    'speed_factor': speed_factor
                },
                speaker_count=len(set(s.speaker for s in transcription_segments if s.speaker)) if speaker_info else None
            )

            if progress_callback:
                progress_callback(f"Completed! Processed {duration:.1f}s in {processing_time:.1f}s ({speed_factor:.1f}x speed)")

            self.logger.info(f"Transcription completed: {speed_factor:.1f}x real-time, {len(transcription_segments)} segments")

            return result

        except Exception as e:
            self.logger.error(f"Transcription error: {str(e)}")
            raise

    def _perform_diarization(self, audio_path: str) -> Optional[Dict]:
        """Perform speaker diarization on audio file."""
        try:
            if not self.diarization_pipeline:
                return None

            self.logger.info("Performing speaker diarization...")

            # Run diarization
            diarization = self.diarization_pipeline(audio_path)

            # Convert to our format
            speakers = {}
            for turn, _, speaker in diarization.itertracks(yield_label=True):
                if speaker not in speakers:
                    speakers[speaker] = []
                speakers[speaker].append({
                    'start': turn.start,
                    'end': turn.end
                })

            self.logger.info(f"Found {len(speakers)} speakers")
            return speakers

        except Exception as e:
            self.logger.warning(f"Diarization failed: {str(e)}")
            return None

    def _assign_speaker_to_segment(self, start: float, end: float, speaker_info: Dict) -> Optional[str]:
        """Assign speaker to transcription segment based on overlap."""
        best_speaker = None
        best_overlap = 0.0

        segment_duration = end - start

        for speaker, turns in speaker_info.items():
            total_overlap = 0.0

            for turn in turns:
                # Calculate overlap between segment and speaker turn
                overlap_start = max(start, turn['start'])
                overlap_end = min(end, turn['end'])
                if overlap_start < overlap_end:
                    overlap_duration = overlap_end - overlap_start
                    total_overlap += overlap_duration

            # Calculate overlap percentage for this speaker
            overlap_percentage = total_overlap / segment_duration if segment_duration > 0 else 0

            if overlap_percentage > best_overlap:
                best_overlap = overlap_percentage
                best_speaker = speaker

        # Only assign speaker if significant overlap (>50%)
        return best_speaker if best_overlap > 0.5 else None

    def _update_stats(self, duration: float, processing_time: float):
        """Update internal processing statistics."""
        self.stats['total_audio_processed'] += duration
        self.stats['total_processing_time'] += processing_time
        self.stats['transcriptions_completed'] += 1

        if self.stats['total_processing_time'] > 0:
            self.stats['average_speed_factor'] = (
                self.stats['total_audio_processed'] / self.stats['total_processing_time']
            )

    def transcribe_live_stream(
        self,
        chunk_callback: Callable[[TranscriptionSegment], None],
        chunk_duration: float = 5.0,
        sample_rate: int = 16000,
        language: Optional[str] = None
    ):
        """
        Transcribe live audio stream with real-time processing.

        Args:
            chunk_callback: Callback function to handle transcribed chunks
            chunk_duration: Duration of each audio chunk in seconds
            sample_rate: Audio sample rate
            language: Language code for transcription
        """
        try:
            import pyaudio
            import queue
            import threading

            # Audio capture settings
            chunk_size = int(sample_rate * chunk_duration)
            audio_queue = queue.Queue()

            def audio_capture():
                """Capture audio in a separate thread."""
                p = pyaudio.PyAudio()

                try:
                    stream = p.open(
                        format=pyaudio.paFloat32,
                        channels=1,
                        rate=sample_rate,
                        input=True,
                        frames_per_buffer=chunk_size
                    )

                    self.logger.info(f"Started live audio capture at {sample_rate}Hz")

                    while self._live_streaming:
                        data = stream.read(chunk_size, exception_on_overflow=False)
                        audio_data = np.frombuffer(data, dtype=np.float32)
                        audio_queue.put(audio_data)

                except Exception as e:
                    self.logger.error(f"Audio capture error: {str(e)}")
                finally:
                    stream.stop_stream()
                    stream.close()
                    p.terminate()

            # Start audio capture thread
            self._live_streaming = True
            capture_thread = threading.Thread(target=audio_capture, daemon=True)
            capture_thread.start()

            segment_counter = 0

            while self._live_streaming:
                try:
                    # Get audio chunk with timeout
                    audio_chunk = audio_queue.get(timeout=1.0)

                    # Save chunk to temporary file
                    temp_path = f"temp_chunk_{segment_counter}.wav"

                    import soundfile as sf
                    sf.write(temp_path, audio_chunk, sample_rate)

                    # Transcribe chunk
                    try:
                        segments, info = self.whisper_model.transcribe(
                            temp_path,
                            language=language,
                            beam_size=1,  # Faster for real-time
                            word_timestamps=False,
                            vad_filter=True
                        )

                        for segment in segments:
                            if segment.text.strip():  # Only process non-empty segments
                                transcription_segment = TranscriptionSegment(
                                    id=segment_counter,
                                    text=segment.text.strip(),
                                    start=segment.start + (segment_counter * chunk_duration),
                                    end=segment.end + (segment_counter * chunk_duration),
                                    confidence=getattr(segment, 'avg_logprob', 0.0),
                                    speaker=None,
                                    words=None
                                )

                                chunk_callback(transcription_segment)

                    except Exception as e:
                        self.logger.warning(f"Chunk transcription error: {str(e)}")

                    finally:
                        # Clean up temp file
                        if os.path.exists(temp_path):
                            os.remove(temp_path)

                    segment_counter += 1

                except queue.Empty:
                    continue  # No audio data available, continue

        except ImportError:
            raise ImportError("Live streaming requires: pip install pyaudio soundfile")
        except Exception as e:
            self.logger.error(f"Live streaming error: {str(e)}")
            raise

    def stop_live_stream(self):
        """Stop live audio streaming."""
        self._live_streaming = False
        self.logger.info("Live streaming stopped")

    def transcribe_batch(
        self,
        audio_files: List[str],
        output_dir: str,
        progress_callback: Optional[Callable] = None,
        **transcribe_kwargs
    ) -> Dict[str, TranscriptionResult]:
        """
        Batch process multiple audio files.

        Args:
            audio_files: List of audio file paths
            output_dir: Directory to save transcription results
            progress_callback: Optional progress callback
            **transcribe_kwargs: Additional arguments for transcribe method

        Returns:
            Dictionary mapping file paths to transcription results
        """
        os.makedirs(output_dir, exist_ok=True)
        results = {}

        for i, audio_file in enumerate(audio_files):
            try:
                if progress_callback:
                    progress_callback(f"Processing file {i+1}/{len(audio_files)}: {os.path.basename(audio_file)}")

                # Transcribe file
                result = self.transcribe(audio_file, **transcribe_kwargs)
                results[audio_file] = result

                # Save result to JSON
                output_file = os.path.join(
                    output_dir,
                    f"{Path(audio_file).stem}_transcription.json"
                )
                self.save_transcription(result, output_file)

                self.logger.info(f"Completed {i+1}/{len(audio_files)}: {audio_file}")

            except Exception as e:
                self.logger.error(f"Failed to process {audio_file}: {str(e)}")
                results[audio_file] = None

        return results

    def save_transcription(self, result: TranscriptionResult, output_path: str, format: str = "json"):
        """
        Save transcription result to file.

        Args:
            result: TranscriptionResult object
            output_path: Path to save the result
            format: Output format (json, txt, srt, vtt)
        """
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        if format.lower() == "json":
            self._save_as_json(result, output_path)
        elif format.lower() == "txt":
            self._save_as_txt(result, output_path)
        elif format.lower() == "srt":
            self._save_as_srt(result, output_path)
        elif format.lower() == "vtt":
            self._save_as_vtt(result, output_path)
        else:
            raise ValueError(f"Unsupported format: {format}")

    def _save_as_json(self, result: TranscriptionResult, output_path: str):
        """Save transcription as JSON."""
        data = {
            'metadata': {
                'language': result.language,
                'duration': result.duration,
                'processing_time': result.processing_time,
                'model_used': result.model_used,
                'source_info': result.source_info,
                'speaker_count': result.speaker_count
            },
            'segments': [
                {
                    'id': seg.id,
                    'text': seg.text,
                    'start': seg.start,
                    'end': seg.end,
                    'confidence': seg.confidence,
                    'speaker': seg.speaker,
                    'words': seg.words
                }
                for seg in result.segments
            ]
        }

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _save_as_txt(self, result: TranscriptionResult, output_path: str):
        """Save transcription as plain text."""
        with open(output_path, 'w', encoding='utf-8') as f:
            for segment in result.segments:
                speaker_prefix = f"[{segment.speaker}] " if segment.speaker else ""
                f.write(f"{speaker_prefix}{segment.text}\n")

    def _save_as_srt(self, result: TranscriptionResult, output_path: str):
        """Save transcription as SRT subtitle file."""
        def format_timestamp(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}".replace('.', ',')

        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(result.segments, 1):
                start_time = format_timestamp(segment.start)
                end_time = format_timestamp(segment.end)

                speaker_prefix = f"[{segment.speaker}] " if segment.speaker else ""
                text = f"{speaker_prefix}{segment.text}"

                f.write(f"{i}\n")
                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

    def _save_as_vtt(self, result: TranscriptionResult, output_path: str):
        """Save transcription as WebVTT file."""
        def format_timestamp(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours:02d}:{minutes:02d}:{secs:06.3f}"

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("WEBVTT\n\n")

            for segment in result.segments:
                start_time = format_timestamp(segment.start)
                end_time = format_timestamp(segment.end)

                speaker_prefix = f"<v {segment.speaker}>" if segment.speaker else ""
                text = f"{speaker_prefix}{segment.text}"

                f.write(f"{start_time} --> {end_time}\n")
                f.write(f"{text}\n\n")

    def get_stats(self) -> Dict:
        """Get processing statistics."""
        return self.stats.copy()

    def set_model(self, model_size: str):
        """
        Switch to a different Whisper model.

        Args:
            model_size: New model size (tiny, base, small, medium, large-v2, large-v3)
        """
        if model_size != self.model_size:
            self.logger.info(f"Switching from {self.model_size} to {model_size}")
            self.model_size = model_size

            # Reload Whisper model
            self.whisper_model = WhisperModel(
                model_size,
                device=self.device,
                compute_type=self.compute_type,
                download_root="./models"
            )

            self.logger.info(f"Model switched to {model_size}")

    def get_supported_languages(self) -> List[str]:
        """Get list of languages supported by Whisper."""
        return [
            'af', 'am', 'ar', 'as', 'az', 'ba', 'be', 'bg', 'bn', 'bo', 'br', 'bs', 'ca', 'cs', 'cy',
            'da', 'de', 'el', 'en', 'es', 'et', 'eu', 'fa', 'fi', 'fo', 'fr', 'gl', 'gu', 'ha', 'haw',
            'he', 'hi', 'hr', 'ht', 'hu', 'hy', 'id', 'is', 'it', 'ja', 'jw', 'ka', 'kk', 'km', 'kn',
            'ko', 'la', 'lb', 'ln', 'lo', 'lt', 'lv', 'mg', 'mi', 'mk', 'ml', 'mn', 'mr', 'ms', 'mt',
            'my', 'ne', 'nl', 'nn', 'no', 'oc', 'pa', 'pl', 'ps', 'pt', 'ro', 'ru', 'sa', 'sd', 'si',
            'sk', 'sl', 'sn', 'so', 'sq', 'sr', 'su', 'sv', 'sw', 'ta', 'te', 'tg', 'th', 'tk', 'tl',
            'tr', 'tt', 'uk', 'ur', 'uz', 've', 'vi', 'yi', 'yo', 'zh'
        ]

    def cleanup(self):
        """Clean up resources and temporary files."""
        self.logger.info("Cleaning up transcription engine...")

        # Stop live streaming if active
        if hasattr(self, '_live_streaming'):
            self._live_streaming = False

        # Clean up any temporary files
        temp_files = [f for f in os.listdir('.') if f.startswith('temp_chunk_') and f.endswith('.wav')]
        for temp_file in temp_files:
            try:
                os.remove(temp_file)
            except:
                pass

        self.logger.info("Cleanup completed")

class TranscriptionEngineFactory:
"""Factory class for creating optimized TranscriptionEngine instances."""

    @staticmethod
    def create_for_accuracy(diarization_token: Optional[str] = None) -> TranscriptionEngine:
        """Create engine optimized for maximum accuracy."""
        return TranscriptionEngine(
            model_size="large-v3",
            enable_diarization=True,
            diarization_token=diarization_token
        )

    @staticmethod
    def create_for_speed() -> TranscriptionEngine:
        """Create engine optimized for speed."""
        return TranscriptionEngine(
            model_size="base",
            enable_diarization=False
        )

    @staticmethod
    def create_for_realtime() -> TranscriptionEngine:
        """Create engine optimized for real-time processing."""
        return TranscriptionEngine(
            model_size="tiny",
            enable_diarization=False
        )

    @staticmethod
    def create_balanced() -> TranscriptionEngine:
        """Create engine with balanced speed and accuracy."""
        return TranscriptionEngine(
            model_size="small",
            enable_diarization=False
        )

# Utility functions for audio processing

def validate_audio_file(file_path: str) -> bool:
"""Validate if file is a supported audio format."""
supported_extensions = {'.wav', '.mp3', '.m4a', '.flac', '.ogg', '.wma', '.aac'}
return Path(file_path).suffix.lower() in supported_extensions

def get_audio_info(file_path: str) -> Dict:
"""Get basic information about audio file."""
try:
duration = librosa.get_duration(filename=file_path)
sample_rate = librosa.get_samplerate(file_path)
file_size = os.path.getsize(file_path)

        return {
            'duration': duration,
            'sample_rate': sample_rate,
            'file_size': file_size,
            'format': Path(file_path).suffix.lower()
        }
    except Exception as e:
        return {'error': str(e)}

# Example usage and testing

if **name** == "**main**": # Example usage
engine = TranscriptionEngineFactory.create_balanced()

    # Test file transcription
    audio_file = "test_audio.wav"
    if os.path.exists(audio_file):
        def progress_update(message):
            print(f"Progress: {message}")

        try:
            result = engine.transcribe(
                audio_file,
                progress_callback=progress_update,
                word_timestamps=True
            )

            print(f"\nTranscription completed!")
            print(f"Language: {result.language}")
            print(f"Duration: {result.duration:.2f}s")
            print(f"Processing time: {result.processing_time:.2f}s")
            print(f"Speed factor: {result.duration/result.processing_time:.1f}x")
            print(f"Segments: {len(result.segments)}")

            # Save results
            engine.save_transcription(result, "output.json", "json")
            engine.save_transcription(result, "output.srt", "srt")

            print(f"\nFirst few segments:")
            for segment in result.segments[:3]:
                print(f"[{segment.start:.1f}s-{segment.end:.1f}s] {segment.text}")

        except Exception as e:
            print(f"Error: {str(e)}")
    else:
        print("No test audio file found. Place a file named 'test_audio.wav' to test.")

    # Print stats
    print(f"\nEngine statistics: {engine.get_stats()}")

    # Cleanup
    engine.cleanup()
