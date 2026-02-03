"""
Instagram Reel Handler - Downloads and transcribes Instagram Reels
With smart Llama-based transcript correction
"""

import os
import re
import subprocess
import tempfile
import shutil
import glob
from typing import Optional, Tuple
import whisper
import instaloader

from .transcript_corrector import TranscriptCorrector


class InstagramHandler:
    """Handles Instagram Reel downloading and audio transcription."""
    
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
        "hinglish": "hi"
    }
    
    def __init__(self, whisper_model: str = "base", groq_api_key: Optional[str] = None):
        self.whisper_model_name = whisper_model
        self.whisper_model = None
        self.groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        self.transcript_corrector = TranscriptCorrector(api_key=self.groq_api_key)
        
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            save_metadata=False,
            download_comments=False,
            download_video_thumbnails=False,
            filename_pattern="{shortcode}"
        )
    
    def _load_whisper_model(self):
        if self.whisper_model is None:
            print(f"[*] Loading Whisper model: {self.whisper_model_name}")
            self.whisper_model = whisper.load_model(self.whisper_model_name)
        return self.whisper_model
    
    @staticmethod
    def extract_shortcode(url: str) -> Optional[str]:
        patterns = [
            r'/(?:reels?|p)/([A-Za-z0-9_-]+)',
            r'instagram\.com/(?:reels?|p)/([A-Za-z0-9_-]+)',
        ]
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        return None
    
    def _find_video_file(self, shortcode: str) -> Optional[str]:
        search_locations = [
            os.path.join(tempfile.gettempdir(), f"reel_{shortcode}"),
            os.getcwd(),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Temp', f"reel_{shortcode}"),
            tempfile.gettempdir(),
        ]
        
        for location in search_locations:
            if not os.path.exists(location):
                continue
            for pattern in [f"*{shortcode}*.mp4", "*.mp4"]:
                matches = glob.glob(os.path.join(location, pattern))
                if matches:
                    return matches[0]
            for root, dirs, files in os.walk(location):
                for f in files:
                    if f.endswith(".mp4") and shortcode in f:
                        return os.path.join(root, f)
        
        return None

    def download_reel(self, url: str) -> Tuple[str, str]:
        shortcode = self.extract_shortcode(url)
        if not shortcode:
            raise ValueError("Invalid Instagram URL.")
        
        temp_dir = os.path.join(tempfile.gettempdir(), f"reel_{shortcode}")
        
        if os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        os.makedirs(temp_dir, exist_ok=True)
        
        original_dir = os.getcwd()
        
        try:
            os.chdir(temp_dir)
            print(f"[*] Downloading Reel: {shortcode}")
            
            post = instaloader.Post.from_shortcode(self.loader.context, shortcode)
            self.loader.download_post(post, target=temp_dir)
            
            os.chdir(original_dir)
            
            video_path = self._find_video_file(shortcode)
            
            if not video_path:
                all_mp4 = glob.glob(os.path.join(temp_dir, "**", "*.mp4"), recursive=True)
                if all_mp4:
                    video_path = all_mp4[0]
            
            if not video_path:
                raise ValueError("No video file found.")
            
            print(f"[*] Video found: {video_path}")
            
            # Extract audio
            audio_path = os.path.join(temp_dir, "audio.mp3")
            print("[*] Extracting audio...")
            
            result = subprocess.run(
                ["ffmpeg", "-i", video_path, "-q:a", "0", "-map", "a", audio_path, "-y"],
                capture_output=True, text=True
            )
            
            if not os.path.exists(audio_path):
                raise ValueError("Audio extraction failed.")
            
            print(f"[*] Audio extracted: {audio_path}")
            return video_path, audio_path
            
        except Exception as e:
            os.chdir(original_dir)
            raise e
    
    def transcribe(self, audio_path: str, language: str = "english") -> dict:
        lang_code = self.SUPPORTED_LANGUAGES.get(language.lower())
        
        model = self._load_whisper_model()
        print(f"[*] Transcribing audio in {language}...")
        
        if lang_code:
            result = model.transcribe(audio_path, language=lang_code)
        else:
            result = model.transcribe(audio_path)
        
        original_transcript = result["text"]
        if isinstance(original_transcript, list):
            original_transcript = " ".join(original_transcript)
        print(f"[*] Raw transcript: {original_transcript[:100]}...")
        
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
    
    def process_reel(self, url: str, language: str = "english") -> dict:
        video_path, audio_path = self.download_reel(url)
        
        try:
            transcription = self.transcribe(audio_path, language)
            
            return {
                "url": url,
                "shortcode": self.extract_shortcode(url),
                "transcript": transcription["transcript"],
                "original_transcript": transcription.get("original_transcript", ""),
                "detected_language": transcription["detected_language"],
                "segments": transcription["segments"],
                "video_path": video_path,
                "audio_path": audio_path,
                "corrections_applied": transcription.get("corrections_applied", False),
                "correction_method": transcription.get("correction_method", "none")
            }
        except Exception as e:
            self.cleanup(video_path)
            raise e
    
    def cleanup(self, video_path: str):
        if video_path:
            temp_dir = os.path.dirname(video_path)
            if temp_dir and os.path.exists(temp_dir) and "reel_" in temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)