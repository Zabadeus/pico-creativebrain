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