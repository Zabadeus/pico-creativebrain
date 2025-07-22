"""
File management service for PICO application.
"""
import os
import json
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import logging

from core.exceptions import StorageError
from core.events import event_bus, Event, EventType
from models.data_models import SessionMetadata, KnowledgeData
from utils.file import ensure_directory, get_file_size, file_exists
from utils.logger import get_logger

logger = get_logger(__name__)

class FileManager:
    """
    Manages persistent file storage for transcription sessions with hierarchical organization.
    """
    
    def __init__(self, base_path: str = "transcripts", auto_create: bool = True):
        """
        Initialize the file manager.
        
        Args:
            base_path: Root directory for all transcript storage
            auto_create: Whether to automatically create directories
        """
        self.base_path = Path(base_path)
        self.auto_create = auto_create
        
        if auto_create:
            ensure_directory(self.base_path)
        
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
        
        self.knowledge_files = {
            'tags': 'knowledge/tags.json',
            'links': 'knowledge/links.json', 
            'insights': 'knowledge/insights.md'
        }
        
        logger.info(f"FileManager initialized with base path: {self.base_path}")
    
    def create_session(self, session_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a new session with directory structure.
        
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
                privacy_mode="full",
                ai_processed=False
            )
            
            # Update with provided metadata
            if metadata:
                for key, value in metadata.items():
                    if hasattr(initial_metadata, key):
                        setattr(initial_metadata, key, value)
            
            # Save metadata
            self.save_session_metadata(session_id, initial_metadata)
            
            # Publish event
            event_bus.publish(Event(
                type=EventType.SESSION_CREATED,
                data={"session_id": session_id},
                timestamp=datetime.now().timestamp()
            ))
            
            logger.info(f"Session {session_id} created successfully")
            return session_id
            
        except Exception as e:
            # Cleanup on failure
            if session_path.exists():
                shutil.rmtree(session_path)
            logger.error(f"Failed to create session {session_id}: {str(e)}")
            raise StorageError(f"Failed to create session {session_id}: {str(e)}")
    
    def save_session_metadata(self, session_id: str, metadata: SessionMetadata) -> None:
        """Save session metadata."""
        session_path = self._get_session_path(session_id)
        metadata_file = session_path / "metadata.json"
        
        try:
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata.__dict__, f, indent=2)
                
            # Update the updated timestamp
            metadata.updated = datetime.now().isoformat()
            
            logger.debug(f"Metadata saved for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save metadata for session {session_id}: {str(e)}")
            raise StorageError(f"Failed to save metadata for session {session_id}: {str(e)}")
    
    def load_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """Load session metadata."""
        session_path = self._get_session_path(session_id)
        metadata_file = session_path / "metadata.json"
        
        if not metadata_file.exists():
            return None
        
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SessionMetadata(**data)
            
        except Exception as e:
            logger.error(f"Failed to load metadata for session {session_id}: {str(e)}")
            raise StorageError(f"Failed to load metadata for session {session_id}: {str(e)}")
    
    def save_audio_file(self, session_id: str, audio_data: bytes, filename: str = "original.wav") -> str:
        """
        Save audio file to session.
        
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
            
            logger.debug(f"Audio file saved for session {session_id}")
            return str(audio_file)
            
        except Exception as e:
            logger.error(f"Failed to save audio file for session {session_id}: {str(e)}")
            raise StorageError(f"Failed to save audio file for session {session_id}: {str(e)}")
    
    def save_knowledge_data(self, session_id: str, knowledge: KnowledgeData) -> None:
        """
        Save knowledge management data.
        
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
                
            logger.debug(f"Knowledge data saved for session {session_id}")
            
        except Exception as e:
            logger.error(f"Failed to save knowledge data for session {session_id}: {str(e)}")
            raise StorageError(f"Failed to save knowledge data for session {session_id}: {str(e)}")
    
    def load_knowledge_data(self, session_id: str) -> Optional[KnowledgeData]:
        """
        Load knowledge management data.
        
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
            logger.error(f"Failed to load knowledge data for session {session_id}: {str(e)}")
            raise StorageError(f"Failed to load knowledge data for session {session_id}: {str(e)}")
    
    def export_session(self, session_id: str, export_format: str, include_audio: bool = True) -> str:
        """
        Export complete session in specified format.
        
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
        List all available sessions.
        
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
                        'metadata': metadata.__dict__ if metadata else None
                    })
                else:
                    sessions.append(item.name)
        
        return sessions
    
    def delete_session(self, session_id: str, confirm: bool = False) -> None:
        """
        Delete a session and all its data.
        
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
            logger.info(f"Session {session_id} deleted successfully")
        except Exception as e:
            logger.error(f"Failed to delete session {session_id}: {str(e)}")
            raise StorageError(f"Failed to delete session {session_id}: {str(e)}")
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get comprehensive statistics for a session"""
        session_path = self._get_session_path(session_id)
        
        if not session_path.exists():
            raise StorageError(f"Session {session_id} does not exist")
        
        stats = {
            'session_id': session_id,
            'total_size_bytes': get_file_size(session_path),
            'files_count': len(list(session_path.rglob('*'))),
            'directories': {},
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
                    'size_bytes': get_file_size(dir_path)
                }
        
        # Check for audio and knowledge data
        stats['has_audio'] = (session_path / "audio" / "original.wav").exists()
        stats['has_knowledge_data'] = (session_path / "knowledge").exists()
        
        return stats
    
    # Private helper methods
    
    def _ensure_base_directory(self) -> None:
        """Ensure base directory exists"""
        ensure_directory(self.base_path)
    
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
            ensure_directory(directory)
    
    def _parse_insights_markdown(self, content: str) -> tuple:
        """Parse insights markdown content."""
        insights = []
        key_points = []
        created = updated = datetime.now().isoformat()
        
        lines = content.split('\n')
        current_section = None
        
        for line in lines:
            if line.startswith('**Generated:**'):
                created = line.replace('**Generated:**', '').strip()
            elif line.startswith('**Updated:**'):
                updated = line.replace('**Updated:**', '').strip()
            elif line.startswith('## Key Points'):
                current_section = 'key_points'
            elif line.startswith('## Detailed Insights'):
                current_section = 'insights'
            elif line.startswith('- ') and current_section == 'key_points':
                key_points.append(line[2:].strip())
            elif current_section == 'insights' and line.strip():
                insights.append(line.strip())
        
        return insights, key_points, created, updated
    
    def _export_session_json(self, session_id: str, exports_dir: Path, timestamp: str, include_audio: bool) -> str:
        """Export session as JSON."""
        session_path = self._get_session_path(session_id)
        export_file = exports_dir / f"session_{timestamp}.json"
        
        # Build session data
        session_data = {
            'session_id': session_id,
            'metadata': None,
            'audio': None,
            'versions': {},
            'knowledge': None,
            'exports': []
        }
        
        # Add metadata
        metadata = self.load_session_metadata(session_id)
        if metadata:
            session_data['metadata'] = metadata.__dict__
        
        # Add audio info
        if include_audio:
            audio_path = session_path / "audio" / "original.wav"
            if audio_path.exists():
                session_data['audio'] = {
                    'path': str(audio_path),
                    'size': get_file_size(str(audio_path))
                }
        
        # Add versions
        versions_dir = session_path / "versions"
        if versions_dir.exists():
            for version_file in versions_dir.glob("*.md"):
                with open(version_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                session_data['versions'][version_file.stem] = content
        
        # Add knowledge
        knowledge = self.load_knowledge_data(session_id)
        if knowledge:
            session_data['knowledge'] = knowledge.__dict__
        
        # Add exports
        exports_path = session_path / "exports"
        if exports_path.exists():
            for export_file in exports_path.glob("*"):
                session_data['exports'].append({
                    'name': export_file.name,
                    'size': get_file_size(str(export_file))
                })
        
        # Save JSON
        with open(export_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, indent=2, ensure_ascii=False)
        
        return str(export_file)
    
    def _export_session_zip(self, session_id: str, exports_dir: Path, timestamp: str, include_audio: bool) -> str:
        """Export session as ZIP."""
        import zipfile
        
        session_path = self._get_session_path(session_id)
        export_file = exports_dir / f"session_{timestamp}.zip"
        
        with zipfile.ZipFile(export_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add metadata
            metadata_file = session_path / "metadata.json"
            if metadata_file.exists():
                zipf.write(metadata_file, f"{session_id}/metadata.json")
            
            # Add audio
            if include_audio:
                audio_dir = session_path / "audio"
                if audio_dir.exists():
                    for file_path in audio_dir.rglob("*"):
                        if file_path.is_file():
                            arcname = f"{session_id}/audio/{file_path.relative_to(audio_dir)}"
                            zipf.write(file_path, arcname)
            
            # Add versions
            versions_dir = session_path / "versions"
            if versions_dir.exists():
                for file_path in versions_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = f"{session_id}/versions/{file_path.relative_to(versions_dir)}"
                        zipf.write(file_path, arcname)
            
            # Add knowledge
            knowledge_dir = session_path / "knowledge"
            if knowledge_dir.exists():
                for file_path in knowledge_dir.rglob("*"):
                    if file_path.is_file():
                        arcname = f"{session_id}/knowledge/{file_path.relative_to(knowledge_dir)}"
                        zipf.write(file_path, arcname)
            
            # Add exports
            exports_path = session_path / "exports"
            if exports_path.exists():
                for file_path in exports_path.rglob("*"):
                    if file_path.is_file() and file_path != export_file:
                        arcname = f"{session_id}/exports/{file_path.relative_to(exports_path)}"
                        zipf.write(file_path, arcname)
        
        return str(export_file)
    
    def _export_session_html(self, session_id: str, exports_dir: Path, timestamp: str) -> str:
        """Export session as HTML."""
        session_path = self._get_session_path(session_id)
        export_file = exports_dir / f"session_{timestamp}.html"
        
        # Get metadata
        metadata = self.load_session_metadata(session_id)
        
        # Build HTML content
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>PICO Session - {session_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 1200px; margin: 0 auto; padding: 20px; }}
        h1, h2, h3 {{ color: #2c3e50; }}
        .session-info {{ background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
        .version {{ margin-bottom: 30px; }}
        .version h3 {{ border-bottom: 1px solid #eee; padding-bottom: 5px; }}
        .knowledge {{ background: #f8f9fa; padding: 15px; border-radius: 5px; }}
        .export-link {{ display: inline-block; margin-top: 10px; padding: 8px 15px; background: #007bff; color: white; text-decoration: none; border-radius: 4px; }}
        .export-link:hover {{ background: #0056b3; }}
    </style>
</head>
<body>
    <h1>PICO Session: {session_id}</h1>
    
    <div class="session-info">
        <h2>Session Information</h2>
        <p><strong>Created:</strong> {metadata.created if metadata else 'Unknown'}</p>
        <p><strong>Updated:</strong> {metadata.updated if metadata else 'Unknown'}</p>
        <p><strong>Duration:</strong> {metadata.duration if metadata else 'Unknown'}</p>
        <p><strong>Privacy Mode:</strong> {metadata.privacy_mode if metadata else 'Unknown'}</p>
        <p><strong>AI Processed:</strong> {'Yes' if metadata and metadata.ai_processed else 'No'}</p>
    </div>
"""

        # Add versions
        versions_dir = session_path / "versions"
        if versions_dir.exists():
            for version_file in sorted(versions_dir.glob("*.md")):
                with open(version_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Convert markdown to HTML (simplified)
                html_content += f"""
    <div class="version">
        <h3>{version_file.stem.replace('_', ' ').title()}</h3>
        <div>{content.replace('#', '<h4>').replace('##', '<h5>').replace('\n', '<br>')}</div>
    </div>
"""
        
        # Add knowledge
        knowledge = self.load_knowledge_data(session_id)
        if knowledge:
            html_content += f"""
    <div class="knowledge">
        <h2>Knowledge</h2>
        <h3>Tags</h3>
        <p>{', '.join(knowledge.tags)}</p>
        
        <h3>Key Points</h3>
        <ul>
"""
            for point in knowledge.key_points:
                html_content += f"<li>{point}</li>"
            html_content += """
        </ul>
        
        <h3>Insights</h3>
"""
            for insight in knowledge.insights:
                html_content += f"<p>{insight}</p>"
            html_content += """
    </div>
"""
        
        # Add export link
        html_content += f"""
    <a href="session_{timestamp}.json" class="export-link">Download JSON Export</a>
    <a href="session_{timestamp}.zip" class="export-link">Download ZIP Export</a>
"""
        
        # Close HTML
        html_content += """
</body>
</html>"""
        
        # Save HTML file
        with open(export_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # Create JSON export
        self._export_session_json(session_id, exports_dir, timestamp, include_audio=False)
        
        # Create ZIP export
        self._export_session_zip(session_id, exports_dir, timestamp, include_audio=False)
        
        return str(export_file)