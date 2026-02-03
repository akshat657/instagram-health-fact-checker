"""
Instagram Reel Handler - Downloads and transcribes Instagram Reels
Using yt-dlp (more reliable than instaloader)
With smart Llama-based transcript correction
"""

import os
import re
import subprocess
import tempfile
import shutil
import glob
from typing import Optional, Tuple, Dict
import whisper
import hashlib
from pathlib import Path

from .transcript_corrector import TranscriptCorrector


class InstagramHandler:
    """Handles Instagram Reel downloading and audio transcription using yt-dlp."""
    
    SUPPORTED_LANGUAGES = {
        "hindi": "hi",
        "english": "en", 
        "urdu": "ur",
        "punjabi": "pa",
        "spanish": "es",
        "french": "fr",
        "german": "de",
        "arabic": "ar",
        "bengali": "bn",
        "tamil": "ta",
        "telugu": "te",
        "marathi": "mr",
        "gujarati": "gu",
        "hinglish": "hi",
        "mandarin": "zh",
        "japanese": "ja",
        "korean": "ko",
        "portuguese": "pt",
        "italian": "it",
        "russian": "ru"
    }
    
    def __init__(self, whisper_model: str = "base", groq_api_key: Optional[str] = None):
        self.whisper_model_name = whisper_model
        self.whisper_model = None
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.transcript_corrector = TranscriptCorrector(api_key=self.groq_api_key)
        
        # Cache directory
        self.cache_dir = Path(tempfile.gettempdir()) / "insta_reel_cache"
        self.cache_dir.mkdir(exist_ok=True)
        
        # Check if yt-dlp is installed
        self._check_ytdlp()
    
    def _check_ytdlp(self):
        """Check if yt-dlp is installed"""
        try:
            result = subprocess.run(
                ["yt-dlp", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                print(f"[*] yt-dlp version: {result.stdout.strip()}")
            else:
                raise FileNotFoundError
        except (FileNotFoundError, subprocess.TimeoutExpired):
            raise RuntimeError(
                "yt-dlp not found. Please install it:\n"
                "pip install yt-dlp\n"
                "Or download from: https://github.com/yt-dlp/yt-dlp"
            )
    
    def _load_whisper_model(self):
        """Lazy load Whisper model"""
        if self.whisper_model is None:
            print(f"[*] Loading Whisper model: {self.whisper_model_name}")
            self.whisper_model = whisper.load_model(self.whisper_model_name)
        return self.whisper_model
    
    @staticmethod
    def extract_shortcode(url: str) -> Optional[str]:
        """Extract Instagram shortcode from URL"""
        patterns = [
            r'/(?:reels?|p)/([A-Za-z0-9_-]+)',
            r'instagram\.com/(?:reels?|p)/([A-Za-z0-9_-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _get_cache_key(self, shortcode: str, language: str) -> str:
        """Generate cache key for transcript"""
        return hashlib.md5(f"{shortcode}_{language}".encode()).hexdigest()
    
    def _get_cached_transcript(self, shortcode: str, language: str) -> Optional[Dict]:
        """Check if transcript is cached"""
        cache_key = self._get_cache_key(shortcode, language)
        cache_file = self.cache_dir / f"{cache_key}.txt"
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    print(f"[*] Using cached transcript for {shortcode}")
                    return {
                        "transcript": content,
                        "cached": True
                    }
            except Exception as e:
                print(f"[!] Cache read error: {e}")
        
        return None
    
    def _cache_transcript(self, shortcode: str, language: str, transcript: str):
        """Cache transcript for future use"""
        try:
            cache_key = self._get_cache_key(shortcode, language)
            cache_file = self.cache_dir / f"{cache_key}.txt"
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                f.write(transcript)
            
            print(f"[*] Cached transcript for {shortcode}")
        except Exception as e:
            print(f"[!] Cache write error: {e}")

    def download_reel(self, url: str) -> Tuple[str, str]:
        """Download Instagram Reel using yt-dlp and extract audio"""
        shortcode = self.extract_shortcode(url)
        if not shortcode:
            raise ValueError("Invalid Instagram URL. Please provide a valid reel/post URL.")
        
        temp_dir = os.path.join(tempfile.gettempdir(), f"reel_{shortcode}")
        
        # Clean up old temp directory if exists
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        video_path = os.path.join(temp_dir, f"{shortcode}.mp4")
        audio_path = os.path.join(temp_dir, "audio.mp3")
        
        try:
            print(f"[*] Downloading Reel: {shortcode}")
            
            # Download with yt-dlp
            cmd = [
                "yt-dlp",
                "-f", "best",  # Best quality
                "-o", video_path,  # Output path
                "--no-playlist",  # Don't download playlists
                "--no-warnings",  # Suppress warnings
                url
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120  # 2 minute timeout
            )
            
            if result.returncode != 0:
                error_msg = result.stderr or result.stdout
                if "Private video" in error_msg or "not available" in error_msg:
                    raise ValueError("This video is private or not available. Please check the URL.")
                elif "Login required" in error_msg:
                    raise ValueError("This video requires login. It may be age-restricted or private.")
                else:
                    raise ValueError(f"Failed to download video: {error_msg[:200]}")
            
            # Check if video was downloaded
            if not os.path.exists(video_path):
                # yt-dlp might have saved with different name
                mp4_files = glob.glob(os.path.join(temp_dir, "*.mp4"))
                if mp4_files:
                    video_path = mp4_files[0]
                else:
                    raise ValueError("Video file not found after download.")
            
            print(f"[*] Video downloaded: {video_path}")
            
            # Extract audio using ffmpeg
            print("[*] Extracting audio...")
            
            result = subprocess.run(
                ["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y"],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if not os.path.exists(audio_path):
                raise ValueError("Audio extraction failed. The video may not have audio.")
            
            print(f"[*] Audio extracted: {audio_path}")
            return video_path, audio_path
            
        except subprocess.TimeoutExpired:
            raise ValueError("Download timed out. Please try again or check your internet connection.")
        except Exception as e:
            # Clean up on error
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
            raise e
    
    def transcribe(self, audio_path: str, language: str = "english") -> dict:
        """Transcribe audio to text with AI correction"""
        lang_code = self.SUPPORTED_LANGUAGES.get(language.lower())
        
        model = self._load_whisper_model()
        print(f"[*] Transcribing audio in {language}...")
        
        # Transcribe with Whisper
        if lang_code:
            result = model.transcribe(audio_path, language=lang_code, fp16=False)
        else:
            result = model.transcribe(audio_path, fp16=False)
        
        original_transcript = result["text"]
        if isinstance(original_transcript, list):
            original_transcript = " ".join(original_transcript)
        
        print(f"[*] Raw transcript ({len(original_transcript)} chars): {original_transcript[:100]}...")
        
        # Smart correction using Llama AI
        correction_result = self.transcript_corrector.correct(original_transcript)
        
        return {
            "transcript": correction_result["corrected"],
            "original_transcript": original_transcript,
            "detected_language": result.get("language", language),
            "segments": result.get("segments", []),
            "corrections_applied": correction_result["corrections_made"],
            "correction_method": correction_result["method"]
        }
    
    def process_reel(self, url: str, language: str = "english", use_cache: bool = True) -> dict:
        """Process Instagram Reel: download, transcribe, and correct"""
        shortcode = self.extract_shortcode(url)
        
        # Check cache first
        if use_cache and shortcode:
            cached = self._get_cached_transcript(shortcode, language)
            if cached:
                return {
                    "url": url,
                    "shortcode": shortcode,
                    "transcript": cached["transcript"],
                    "original_transcript": cached["transcript"],
                    "detected_language": language,
                    "segments": [],
                    "video_path": None,
                    "audio_path": None,
                    "corrections_applied": False,
                    "correction_method": "cached",
                    "cached": True
                }
        
        # Download and transcribe
        video_path, audio_path = self.download_reel(url)
        
        try:
            transcription = self.transcribe(audio_path, language)
            
            # Cache the result
            if shortcode:
                self._cache_transcript(shortcode, language, transcription["transcript"])
            
            return {
                "url": url,
                "shortcode": shortcode,
                "transcript": transcription["transcript"],
                "original_transcript": transcription.get("original_transcript", ""),
                "detected_language": transcription["detected_language"],
                "segments": transcription["segments"],
                "video_path": video_path,
                "audio_path": audio_path,
                "corrections_applied": transcription.get("corrections_applied", False),
                "correction_method": transcription.get("correction_method", "none"),
                "cached": False
            }
        except Exception as e:
            self.cleanup(video_path)
            raise e
    
    def cleanup(self, video_path: str):
        """Clean up temporary files"""
        if video_path:
            temp_dir = os.path.dirname(video_path)
            if temp_dir and os.path.exists(temp_dir) and "reel_" in temp_dir:
                try:
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    print(f"[*] Cleaned up: {temp_dir}")
                except Exception as e:
                    print(f"[!] Cleanup error: {e}")