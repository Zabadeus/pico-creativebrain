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
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import asdict

# Import from centralized models and helpers
from models.data_models import (
    ContentVersion, VersionType, SessionMetadata, KnowledgeData, PrivacyMode, 
    StorageError, TimestampedSegment
)
from utils.helpers import (
    generate_session_id, format_duration_from_seconds, get_directory_size, 
    format_file_size
)

# Assuming ContentVersionManager is in the same services directory
try:
    from .content_manager import ContentVersionManager
except (ImportError, ModuleNotFoundError):
    ContentVersionManager = None # Fallback if not available


class FileStorageManager:
    """
    Manages persistent file storage for transcription sessions with hierarchical organization.
    Integrates with ContentVersionManager for version management.
    """
    
    def __init__(self, base_path: str = "transcripts", auto_create: bool = True):
        self.base_path = Path(base_path)
        if auto_create:
            self.base_path.mkdir(parents=True, exist_ok=True)
        
        self.version_files = {
            VersionType.ORIGINAL: 'versions/original.md',
            VersionType.CLEANED: 'versions/cleaned.md',
            VersionType.SUMMARY_BRIEF: 'versions/summary_brief.md',
            VersionType.SUMMARY_DETAILED: 'versions/summary_detailed.md',
            VersionType.SUMMARY_KEYPOINTS: 'versions/keypoints.md'
        }
    
    def create_session(self, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        if not session_id:
            session_id = generate_session_id()
        
        session_path = self.base_path / session_id
        if session_path.exists():
            raise StorageError(f"Session {session_id} already exists")
        
        try:
            self._create_session_directories(session_path)
            
            initial_metadata = SessionMetadata(
                session_id=session_id,
                created=datetime.now().isoformat(),
                updated=datetime.now().isoformat(),
                duration="00:00:00",
                speaker_count=1,
                privacy_mode=PrivacyMode.PRIVATE.value,
                ai_processed=False,
                tags=[],
                description=""
            )
            
            if metadata:
                for key, value in metadata.items():
                    if hasattr(initial_metadata, key):
                        setattr(initial_metadata, key, value)
            
            self.save_session_metadata(session_id, initial_metadata)
            return session_id
            
        except Exception as e:
            if session_path.exists():
                shutil.rmtree(session_path)
            raise StorageError(f"Failed to create session {session_id}: {str(e)}") from e
    
    def save_content_version(self, session_id: str, version: ContentVersion, content_manager: Optional[Any] = None) -> None:
        session_path = self._get_session_path(session_id)
        version_file = session_path / self.version_files[version.version_type]
        version_file.parent.mkdir(parents=True, exist_ok=True)
        
        markdown_content = self._create_markdown_with_metadata(version, session_id, content_manager)
        
        try:
            version_file.write_text(markdown_content, encoding='utf-8')
            self._update_session_timestamp(session_id)
        except Exception as e:
            raise StorageError(f"Failed to save version {version.version_type.value} for session {session_id}: {str(e)}") from e

    def load_content_version(self, session_id: str, version_type: VersionType) -> Optional[ContentVersion]:
        session_path = self._get_session_path(session_id)
        version_file = session_path / self.version_files[version_type]
        
        if not version_file.exists():
            return None
        
        try:
            content = version_file.read_text(encoding='utf-8')
            return self._parse_markdown_content(content, version_type)
        except Exception as e:
            raise StorageError(f"Failed to load version {version_type.value} for session {session_id}: {str(e)}") from e

    def save_audio_file(self, session_id: str, audio_data: bytes, filename: str = "original.wav") -> str:
        session_path = self._get_session_path(session_id)
        audio_dir = session_path / "audio"
        audio_dir.mkdir(parents=True, exist_ok=True)
        audio_file = audio_dir / filename
        
        try:
            audio_file.write_bytes(audio_data)
            metadata = self.load_session_metadata(session_id)
            if metadata:
                metadata.source_file = filename
                metadata.file_size = len(audio_data)
                metadata.updated = datetime.now().isoformat()
                self.save_session_metadata(session_id, metadata)
            return str(audio_file)
        except Exception as e:
            raise StorageError(f"Failed to save audio file for session {session_id}: {str(e)}") from e

    def save_knowledge_data(self, session_id: str, knowledge: KnowledgeData) -> None:
        session_path = self._get_session_path(session_id)
        knowledge_dir = session_path / "knowledge"
        knowledge_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            tags_data = {
                'all_tags': knowledge.tags,
                'auto_tags': knowledge.auto_tags,
                'manual_tags': knowledge.manual_tags,
                'topics': knowledge.topics,
                'created': knowledge.created,
                'updated': knowledge.updated
            }
            (knowledge_dir / "tags.json").write_text(json.dumps(tags_data, indent=2), encoding='utf-8')
            (knowledge_dir / "links.json").write_text(json.dumps(knowledge.links, indent=2), encoding='utf-8')
            
            insights_content = f"# Insights - {session_id}\n\n"
            insights_content += f"**Generated:** {knowledge.created}\n"
            insights_content += f"**Updated:** {knowledge.updated}\n\n"
            if knowledge.key_points:
                insights_content += "## Key Points\n\n" + "".join(f"- {p}\n" for p in knowledge.key_points) + "\n"
            if knowledge.insights:
                insights_content += "## Detailed Insights\n\n" + "\n\n".join(knowledge.insights)
            (knowledge_dir / "insights.md").write_text(insights_content, encoding='utf-8')
                
        except Exception as e:
            raise StorageError(f"Failed to save knowledge data for session {session_id}: {str(e)}") from e

    def load_knowledge_data(self, session_id: str) -> Optional[KnowledgeData]:
        session_path = self._get_session_path(session_id)
        knowledge_dir = session_path / "knowledge"
        if not knowledge_dir.exists():
            return None
        
        try:
            tags_file = knowledge_dir / "tags.json"
            tags_data = json.loads(tags_file.read_text(encoding='utf-8')) if tags_file.exists() else {}
            
            links_file = knowledge_dir / "links.json"
            links_data = json.loads(links_file.read_text(encoding='utf-8')) if links_file.exists() else {}
            
            insights_file = knowledge_dir / "insights.md"
            insights, key_points, created, updated = (
                self._parse_insights_markdown(insights_file.read_text(encoding='utf-8'))
                if insights_file.exists()
                else ([], [], datetime.now().isoformat(), datetime.now().isoformat())
            )
            
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
            raise StorageError(f"Failed to load knowledge data for session {session_id}: {str(e)}") from e

    def save_session_metadata(self, session_id: str, metadata: SessionMetadata) -> None:
        session_path = self._get_session_path(session_id)
        metadata_file = session_path / "metadata.json"
        try:
            metadata_file.write_text(json.dumps(asdict(metadata), indent=2), encoding='utf-8')
        except Exception as e:
            raise StorageError(f"Failed to save metadata for session {session_id}: {str(e)}") from e

    def load_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        session_path = self._get_session_path(session_id)
        metadata_file = session_path / "metadata.json"
        if not metadata_file.exists():
            return None
        try:
            data = json.loads(metadata_file.read_text(encoding='utf-8'))
            # Ensure all fields are present, providing defaults for older metadata files
            for field in SessionMetadata.__dataclass_fields__:
                if field not in data:
                    data[field] = SessionMetadata.__dataclass_fields__[field].default
            return SessionMetadata(**data)
        except Exception as e:
            raise StorageError(f"Failed to load metadata for session {session_id}: {str(e)}") from e

    def list_sessions(self, include_metadata: bool = False) -> List[Union[str, Dict[str, Any]]]:
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
        if not confirm:
            raise StorageError("Session deletion requires explicit confirmation")
        session_path = self._get_session_path(session_id)
        if not session_path.exists():
            raise StorageError(f"Session {session_id} does not exist")
        try:
            shutil.rmtree(session_path)
        except Exception as e:
            raise StorageError(f"Failed to delete session {session_id}: {str(e)}") from e

    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        session_path = self._get_session_path(session_id)
        if not session_path.exists():
            raise StorageError(f"Session {session_id} does not exist")
        
        stats = {
            'session_id': session_id,
            'total_size_bytes': get_directory_size(session_path),
            'total_size_formatted': format_file_size(get_directory_size(session_path)),
            'files_count': len(list(session_path.rglob('*'))),
            'versions_available': [
                vt.value for vt, vf in self.version_files.items() if (session_path / vf).exists()
            ],
            'has_audio': (session_path / "audio" / "original.wav").exists(),
            'has_knowledge_data': (session_path / "knowledge").exists()
        }
        return stats

    # --- Private Helper Methods ---

    def _get_session_path(self, session_id: str) -> Path:
        return self.base_path / session_id

    def _create_session_directories(self, session_path: Path) -> None:
        for sub_dir in ["audio/segments", "versions", "knowledge", "exports"]:
            (session_path / sub_dir).mkdir(parents=True, exist_ok=True)

    def _update_session_timestamp(self, session_id: str) -> None:
        metadata = self.load_session_metadata(session_id)
        if metadata:
            metadata.updated = datetime.now().isoformat()
            self.save_session_metadata(session_id, metadata)

    def _create_markdown_with_metadata(self, version: ContentVersion, session_id: str, content_manager: Optional[Any]) -> str:
        duration_seconds = version.segments[-1].end_time if version.segments else 0
        metadata = {
            'version': version.version_type.value,
            'session_id': session_id,
            'duration': format_duration_from_seconds(duration_seconds),
            'speaker_count': len(set(seg.speaker for seg in version.segments if seg.speaker)),
            'word_count': version.word_count,
            'created': version.created_at.isoformat(),
            'ai_processed': True,
            'segment_count': len(version.segments),
            **version.metadata
        }
        
        yaml_header = "---\n" + "".join([f'{k}: "{v}"\n' if isinstance(v, str) else f'{k}: {v}\n' for k, v in metadata.items()]) + "---\n\n"
        title = f"# Transcript: {version.version_type.value.replace('_', ' ').title()} Version\n\n"
        
        if version.segments:
            content = "".join(
                f"## [{self._format_markdown_timestamp(seg.start_time)}]{' ' + seg.speaker if seg.speaker else ''}\n{seg.text}\n\n"
                for seg in version.segments
            )
        else:
            content = version.full_text
        
        return yaml_header + title + content

    def _parse_markdown_content(self, content: str, version_type: VersionType) -> ContentVersion:
        lines = content.split('\n')
        metadata = {}
        content_start_index = 0
        
        if lines and lines[0] == '---':
            try:
                yaml_end = lines.index('---', 1)
                metadata_lines = lines[1:yaml_end]
                content_start_index = yaml_end + 1
                for line in metadata_lines:
                    if ':' in line:
                        key, value = line.split(':', 1)
                        metadata[key.strip()] = json.loads(value.strip())
            except (ValueError, json.JSONDecodeError):
                pass # Fallback to no metadata if parsing fails

        content_lines = lines[content_start_index:]
        full_text = '\n'.join(content_lines).strip()
        segments = self._parse_segments_from_markdown(content_lines)
        
        return ContentVersion(
            version_type=version_type,
            segments=segments,
            full_text=full_text,
            metadata=metadata,
            created_at=datetime.fromisoformat(metadata.get('created', datetime.now().isoformat())),
            word_count=int(metadata.get('word_count', len(full_text.split())))
        )

    def _parse_segments_from_markdown(self, content_lines: List[str]) -> List[TimestampedSegment]:
        segments = []
        current_segment_data = None
        
        for line in content_lines:
            match = re.match(r'##\s*\[(\d{2}:\d{2})\]\s*(.*)', line)
            if match:
                if current_segment_data:
                    segments.append(self._finalize_segment(current_segment_data, segments))
                
                timestamp_str, speaker_part = match.groups()
                current_segment_data = {
                    'start_time': self._parse_markdown_timestamp(timestamp_str),
                    'speaker': speaker_part.strip() or None,
                    'text_lines': []
                }
            elif current_segment_data and line.strip() and not line.startswith('#'):
                current_segment_data['text_lines'].append(line.strip())
        
        if current_segment_data:
            segments.append(self._finalize_segment(current_segment_data, segments))
            
        return segments

    def _finalize_segment(self, seg_data: dict, all_segments: list) -> TimestampedSegment:
        # Estimate end_time based on the start of the next segment or add a default duration
        # This logic is imperfect and could be improved if more data is available.
        next_start_time = None
        if all_segments:
             # This logic is flawed as it depends on the order of processing.
             # A better approach would be to parse all start times first.
             pass # Placeholder for a better implementation
        
        end_time = next_start_time if next_start_time else seg_data['start_time'] + 5.0 # Default 5s duration
        
        return TimestampedSegment(
            start_time=seg_data['start_time'],
            end_time=end_time,
            text=' '.join(seg_data['text_lines']),
            speaker=seg_data['speaker']
        )

    def _parse_insights_markdown(self, content: str) -> tuple:
        lines = content.split('\n')
        insights, key_points = [], []
        created = updated = datetime.now().isoformat()
        current_section = None
        
        for line in lines:
            if '**Generated:**' in line: created = line.split('**Generated:**')[1].strip()
            elif '**Updated:**' in line: updated = line.split('**Updated:**')[1].strip()
            elif line.startswith('## Key Points'): current_section = 'key_points'
            elif line.startswith('## Detailed Insights'): current_section = 'insights'
            elif line.startswith('- ') and current_section == 'key_points': key_points.append(line[2:].strip())
            elif line.strip() and current_section == 'insights' and not line.startswith('#'): insights.append(line.strip())
        
        return insights, key_points, created, updated

    def _format_markdown_timestamp(self, seconds: float) -> str:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"

    def _parse_markdown_timestamp(self, timestamp_str: str) -> float:
        parts = timestamp_str.split(':')
        return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else 0.0
