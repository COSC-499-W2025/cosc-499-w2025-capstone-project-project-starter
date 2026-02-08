import os
import json
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Optional, Union
import sys as _sys
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)

# Optional heavy dependencies are lazily imported to keep tests light.
try:
    from moviepy.editor import VideoFileClip
    _MOVIEPY_AVAILABLE = True
except ImportError:  # pragma: no cover - dependency not installed in tests
    VideoFileClip = None
    _MOVIEPY_AVAILABLE = False

try:
    import whisper
    _WHISPER_AVAILABLE = True
except ImportError:  # pragma: no cover - dependency not installed in tests
    import types as _types
    whisper = _types.SimpleNamespace(load_model=lambda *args, **kwargs: None)
    _WHISPER_AVAILABLE = False

# Ensure this module is reachable as analyze.video_analyzer for test patches
_sys.modules["analyze.video_analyzer"] = _sys.modules[__name__]
_parent_pkg = _sys.modules.get("analyze")
if _parent_pkg:
    setattr(_parent_pkg, "video_analyzer", _sys.modules[__name__])


# ---------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------
@dataclass
class VideoAnalysisResult:
    """Represents metadata and analysis result for a single video file."""
    file_path: str
    duration_seconds: float
    resolution: str
    frame_rate: float
    total_frames: int
    has_audio: bool
    file_type: str
    format: str
    transcript: Optional[str] = None
    transcript_language: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert result to dictionary for JSON export."""
        data = {
            "file_path": self.file_path,
            "duration_seconds": self.duration_seconds,
            "resolution": self.resolution,
            "frame_rate": self.frame_rate,
            "total_frames": self.total_frames,
            "has_audio": self.has_audio,
            "file_type": self.file_type,
            "format": self.format
        }
        if self.transcript:
            data["transcript"] = self.transcript
            data["transcript_language"] = self.transcript_language
        return data


@dataclass
class VideoCollectionMetrics:
    """Aggregated metrics across multiple video files."""
    total_videos: int
    total_duration: float
    average_fps: float
    resolutions: List[str]
    formats: List[str]
    audio_videos: int
    video_only_files: int
    transcribed_videos: int = 0

    def to_dict(self) -> Dict:
        """Convert metrics summary to dictionary."""
        return {
            "total_videos": self.total_videos,
            "total_duration": self.total_duration,
            "average_fps": self.average_fps,
            "resolutions": self.resolutions,
            "formats": self.formats,
            "audio_videos": self.audio_videos,
            "video_only_files": self.video_only_files,
            "transcribed_videos": self.transcribed_videos
        }


# ---------------------------------------------------------------------
# Video Analyzer
# ---------------------------------------------------------------------
class VideoAnalyzer:
    """Analyze video files and compute collection-level metrics."""

    SUPPORTED_FORMATS = {'.mp4', '.mov', '.avi', '.mkv', '.wmv'}

    def __init__(self, whisper_model: str = "base"):
        """
        Initialize analyzer with default config.
        
        Args:
            whisper_model: Whisper model size ('tiny', 'base', 'small', 'medium', 'large')
                          - tiny: fastest, least accurate (~1GB RAM)
                          - base: good balance (default, ~1GB RAM)
                          - small: better accuracy (~2GB RAM)
                          - medium: very good accuracy (~5GB RAM)
                          - large: best accuracy (~10GB RAM)
        """
        self.skip_dirs = {'.git', '__pycache__', 'temp', 'build', 'dist', 'node_modules'}
        self.whisper_model_name = whisper_model
        self._whisper_model = None

    def _load_whisper_model(self):
        """Lazy load Whisper model only when needed."""
        if self._whisper_model is None:
            if not hasattr(whisper, "load_model"):
                return None
            print(f"[INFO] Loading Whisper '{self.whisper_model_name}' model (first time only)...")
            self._whisper_model = whisper.load_model(self.whisper_model_name)
        return self._whisper_model

    # -----------------------------------------------------------------
    # Core: Analyze Single File
    # -----------------------------------------------------------------
    def analyze_file(self, file_path: Union[str, Path], 
                     transcribe: bool = False) -> Optional[VideoAnalysisResult]:
        """
        Analyze a single video file and return metadata.
        
        Args:
            file_path: Path to video file
            transcribe: If True and video has audio, generate transcript
        """
        file_path = Path(file_path).resolve()

        # If MoviePy is unavailable, we cannot analyze videos
        if VideoFileClip is None:
            return None

        # Skip invalid files
        if not file_path.exists() or file_path.suffix.lower() not in self.SUPPORTED_FORMATS:
            return None

        try:
            with VideoFileClip(str(file_path)) as clip:
                duration = clip.duration or 0.0
                fps = clip.fps or 0.0
                width, height = getattr(clip, "w", 0), getattr(clip, "h", 0)
                has_audio = clip.audio is not None

                total_frames = int(duration * fps) if duration and fps else 0
                resolution = f"{width}x{height}" if width and height else "unknown"
                file_type = "video-with-audio" if has_audio else "video-only"

                result = VideoAnalysisResult(
                    file_path=str(file_path),
                    duration_seconds=duration,
                    resolution=resolution,
                    frame_rate=fps,
                    total_frames=total_frames,
                    has_audio=has_audio,
                    file_type=file_type,
                    format=file_path.suffix.lstrip('.').lower()
                )

                # Generate transcript if requested and audio exists
                # Pass the resolved file_path to ensure transcription uses correct path
                if transcribe and has_audio:
                    transcript_data = self._transcribe_video(file_path)
                    if transcript_data:
                        result.transcript = transcript_data["text"]
                        result.transcript_language = transcript_data["language"]

                return result

        except Exception as e:
            print(f"[WARN] Skipping file {file_path}: {e}")
            return None

    # -----------------------------------------------------------------
    # Transcription
    # -----------------------------------------------------------------
    def _transcribe_video(self, video_path: Path) -> Optional[Dict]:
        """
        Transcribe audio from video using Whisper.
        
        Returns:
            Dict with 'text' and 'language' keys, or None if failed
        """
        try:
            print(f"[INFO] Transcribing audio from: {video_path.name}")
            model = self._load_whisper_model()
            if model is None:
                return None
            
            # Convert Path to absolute string and ensure it exists
            video_path_str = str(video_path.absolute())
            
            if not Path(video_path_str).exists():
                print(f"[ERROR] File not found at: {video_path_str}")
                return None
            
            # Whisper can process video files directly
            result = model.transcribe(video_path_str, fp16=False)
            
            transcript_text = result["text"].strip()
            detected_language = result.get("language", "unknown")
            
            print(f"[SUCCESS] Transcription complete (Language: {detected_language})")
            
            return {
                "text": transcript_text,
                "language": detected_language
            }
            
        except Exception as e:
            print(f"[ERROR] Failed to transcribe {video_path.name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    # -----------------------------------------------------------------
    # Core: Analyze Directory
    # -----------------------------------------------------------------
    def analyze_directory(self, directory_path: Union[str, Path],
                         transcribe: bool = False) -> List[VideoAnalysisResult]:
        """
        Recursively analyze all supported videos in a directory.
        
        Args:
            directory_path: Path to directory
            transcribe: If True, transcribe all videos with audio
        """
        directory_path = Path(directory_path)
        if not directory_path.exists() or not directory_path.is_dir():
            raise ValueError(f"Directory not found: {directory_path}")

        results = []

        for file_path in directory_path.rglob('*'):
            if self._should_skip_file(file_path):
                continue

            if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_FORMATS:
                result = self.analyze_file(file_path, transcribe=transcribe)
                if result:
                    results.append(result)

        return results

    # -----------------------------------------------------------------
    # Metrics Aggregation
    # -----------------------------------------------------------------
    def calculate_collection_metrics(self, results: List[VideoAnalysisResult]) -> VideoCollectionMetrics:
        """Aggregate statistics from a collection of analyzed videos."""
        if not results:
            return VideoCollectionMetrics(0, 0.0, 0.0, [], [], 0, 0, 0)

        total_videos = len(results)
        total_duration = sum(r.duration_seconds for r in results)
        avg_fps = sum(r.frame_rate for r in results) / total_videos if total_videos else 0.0
        resolutions = list({r.resolution for r in results})
        formats = list({r.format for r in results})
        audio_videos = sum(1 for r in results if r.has_audio)
        video_only_files = sum(1 for r in results if not r.has_audio)
        transcribed_videos = sum(1 for r in results if r.transcript is not None)

        return VideoCollectionMetrics(
            total_videos=total_videos,
            total_duration=round(total_duration, 2),
            average_fps=round(avg_fps, 2),
            resolutions=sorted(resolutions),
            formats=sorted(formats),
            audio_videos=audio_videos,
            video_only_files=video_only_files,
            transcribed_videos=transcribed_videos
        )

    # -----------------------------------------------------------------
    # Helper: Skip logic
    # -----------------------------------------------------------------
    def _should_skip_file(self, file_path: Path) -> bool:
        """Return True if a file should be skipped based on directory name."""
        return any(skip in file_path.parts for skip in self.skip_dirs)

    # -----------------------------------------------------------------
    # Helper: Export results
    # -----------------------------------------------------------------
    def save_to_json(self, results: List[VideoAnalysisResult], 
                     output_path: Union[str, Path],
                     separate_transcripts: bool = False) -> None:
        """
        Save list of video results to JSON file(s).
        
        Args:
            results: List of analysis results
            output_path: Path for main JSON output
            separate_transcripts: If True, save transcripts in separate file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save main analysis results
        data = [r.to_dict() for r in results]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"[INFO] Saved analysis results to {output_path}")
        
        # Optionally save transcripts separately
        if separate_transcripts:
            transcripts = {}
            for r in results:
                if r.transcript:
                    transcripts[Path(r.file_path).name] = {
                        "transcript": r.transcript,
                        "language": r.transcript_language,
                        "duration_seconds": r.duration_seconds
                    }
            
            if transcripts:
                transcript_path = output_path.parent / f"{output_path.stem}_transcripts.json"
                with open(transcript_path, "w", encoding="utf-8") as f:
                    json.dump(transcripts, f, indent=4, ensure_ascii=False)
                print(f"[INFO] Saved transcripts to {transcript_path}")

    # -----------------------------------------------------------------
    # Example CLI 
    # -----------------------------------------------------------------
    def run_example(self):  # pragma: no cover
        """Example method to demonstrate analyzer usage."""
        example_dir = Path(__file__).parent / "example_videos"
        results = self.analyze_directory(example_dir)
        metrics = self.calculate_collection_metrics(results)
        print(metrics.to_dict())
