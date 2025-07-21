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
if __name__ == "__main__":
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