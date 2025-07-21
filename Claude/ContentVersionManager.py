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
    LIGHT = "light"      # Basic filler word removal
    MODERATE = "moderate"  # Filler words + basic grammar fixes
    HEAVY = "heavy"      # Full grammar correction + restructuring


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
if __name__ == "__main__":
    # Example usage
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