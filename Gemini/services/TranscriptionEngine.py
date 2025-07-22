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
if __name__ == "__main__":
    # Example usage
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