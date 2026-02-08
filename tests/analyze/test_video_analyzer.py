"""
Unit tests for VideoAnalyzer module.
Covers single file, directory analysis, metrics, transcription, and error handling.
"""

import pytest
import sys, os
from unittest.mock import MagicMock, patch, Mock
from pathlib import Path

# Ensure src is in path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../src')))

from src.analyze.video_analyzer import VideoAnalyzer, VideoAnalysisResult, VideoCollectionMetrics


# ----------------------------
# Fixtures
# ----------------------------

@pytest.fixture
def analyzer():
    """Create a VideoAnalyzer instance."""
    return VideoAnalyzer()


@pytest.fixture
def mock_video_clip():
    """Mock MoviePy VideoFileClip."""
    with patch('analyze.video_analyzer.VideoFileClip') as mock_cls:
        mock_clip = MagicMock()
        mock_clip.__enter__.return_value = mock_clip
        mock_clip.__exit__.return_value = None
        mock_clip.duration = 10.5
        mock_clip.fps = 30.0
        mock_clip.w = 1920
        mock_clip.h = 1080
        mock_clip.audio = MagicMock()  # Has audio
        mock_cls.return_value = mock_clip
        yield mock_clip


@pytest.fixture
def mock_whisper_model():
    """Mock Whisper model for transcription tests."""
    with patch('analyze.video_analyzer.whisper.load_model') as mock_load:
        mock_model = MagicMock()
        mock_model.transcribe.return_value = {
            "text": "This is a test transcript.",
            "language": "en"
        }
        mock_load.return_value = mock_model
        yield mock_model


# ----------------------------
# Tests for single file analysis
# ----------------------------

def test_analyze_file_success(tmp_path, mock_video_clip):
    """Ensure a single video file is analyzed correctly."""
    video_file = tmp_path / "sample.mp4"
    video_file.touch()

    analyzer = VideoAnalyzer()
    result = analyzer.analyze_file(str(video_file))

    assert isinstance(result, VideoAnalysisResult)
    assert result.duration_seconds == pytest.approx(10.5)
    assert result.resolution == "1920x1080"
    assert result.frame_rate == 30.0
    assert result.total_frames == 315
    assert result.has_audio is True
    assert result.file_type == "video-with-audio"
    assert result.format == "mp4"
    assert result.transcript is None  # No transcription by default
    assert result.transcript_language is None


def test_analyze_file_no_audio(tmp_path):
    """Handle video with no audio track."""
    video_file = tmp_path / "mute_video.mov"
    video_file.touch()

    with patch('analyze.video_analyzer.VideoFileClip') as mock_cls:
        mock_clip = MagicMock()
        mock_clip.__enter__.return_value = mock_clip
        mock_clip.__exit__.return_value = None
        mock_clip.duration = 5.0
        mock_clip.fps = 24.0
        mock_clip.w = 1280
        mock_clip.h = 720
        mock_clip.audio = None  # No audio
        mock_cls.return_value = mock_clip

        analyzer = VideoAnalyzer()
        result = analyzer.analyze_file(str(video_file))

        assert isinstance(result, VideoAnalysisResult)
        assert result.file_type == "video-only"
        assert result.has_audio is False
        assert result.format == "mov"
        assert result.transcript is None


def test_analyze_file_invalid_extension(tmp_path, analyzer):
    """Unsupported file extensions should return None."""
    file = tmp_path / "notes.txt"
    file.write_text("this is not a video")

    result = analyzer.analyze_file(str(file))
    assert result is None


def test_analyze_file_not_found(analyzer):
    """Non-existent file should return None safely."""
    result = analyzer.analyze_file("nonexistent.mp4")
    assert result is None


def test_analyze_file_moviepy_error(tmp_path):
    """MoviePy decode failure should be handled gracefully."""
    bad_file = tmp_path / "corrupt.mp4"
    bad_file.touch()

    with patch('analyze.video_analyzer.VideoFileClip', side_effect=Exception("decode fail")):
        analyzer = VideoAnalyzer()
        result = analyzer.analyze_file(str(bad_file))
        assert result is None


# ----------------------------
# Tests for transcription
# ----------------------------

def test_analyze_file_with_transcription(tmp_path, mock_video_clip, mock_whisper_model):
    """Test video analysis with transcription enabled."""
    video_file = tmp_path / "video_with_audio.mp4"
    video_file.touch()

    analyzer = VideoAnalyzer(whisper_model="base")
    result = analyzer.analyze_file(str(video_file), transcribe=True)

    assert isinstance(result, VideoAnalysisResult)
    assert result.has_audio is True
    assert result.transcript == "This is a test transcript."
    assert result.transcript_language == "en"


def test_analyze_file_transcription_no_audio(tmp_path, mock_whisper_model):
    """Transcription should not run if video has no audio."""
    video_file = tmp_path / "silent_video.mp4"
    video_file.touch()

    with patch('analyze.video_analyzer.VideoFileClip') as mock_cls:
        mock_clip = MagicMock()
        mock_clip.__enter__.return_value = mock_clip
        mock_clip.__exit__.return_value = None
        mock_clip.duration = 5.0
        mock_clip.fps = 24.0
        mock_clip.w = 1280
        mock_clip.h = 720
        mock_clip.audio = None  # No audio
        mock_cls.return_value = mock_clip

        analyzer = VideoAnalyzer(whisper_model="tiny")
        result = analyzer.analyze_file(str(video_file), transcribe=True)

        assert result.has_audio is False
        assert result.transcript is None
        assert result.transcript_language is None
        # Whisper should never be called
        mock_whisper_model.transcribe.assert_not_called()


def test_transcription_failure_handled_gracefully(tmp_path, mock_video_clip):
    """If transcription fails, video analysis should still succeed."""
    video_file = tmp_path / "video.mp4"
    video_file.touch()

    with patch('analyze.video_analyzer.whisper.load_model') as mock_load:
        mock_model = MagicMock()
        mock_model.transcribe.side_effect = Exception("Transcription error")
        mock_load.return_value = mock_model

        analyzer = VideoAnalyzer(whisper_model="base")
        result = analyzer.analyze_file(str(video_file), transcribe=True)

        # Video analysis should succeed even if transcription fails
        assert isinstance(result, VideoAnalysisResult)
        assert result.has_audio is True
        assert result.transcript is None  # Transcription failed
        assert result.transcript_language is None


def test_whisper_model_lazy_loading(tmp_path, mock_video_clip, mock_whisper_model):
    """Whisper model should only load when transcription is requested."""
    video_file = tmp_path / "video.mp4"
    video_file.touch()

    with patch('analyze.video_analyzer.whisper.load_model') as mock_load:
        mock_load.return_value = mock_whisper_model

        analyzer = VideoAnalyzer(whisper_model="small")
        
        # Analyze without transcription - model should NOT load
        result1 = analyzer.analyze_file(str(video_file), transcribe=False)
        assert mock_load.call_count == 0
        
        # Analyze with transcription - model should load now
        result2 = analyzer.analyze_file(str(video_file), transcribe=True)
        assert mock_load.call_count == 1


# ----------------------------
# Tests for directory analysis
# ----------------------------

def test_analyze_directory_mixed_files(tmp_path):
    """Ensure analyze_directory processes multiple valid videos."""
    v1 = tmp_path / "video1.mp4"
    v2 = tmp_path / "video2.mov"
    invalid = tmp_path / "readme.txt"
    for f in [v1, v2, invalid]:
        f.touch()

    with patch('analyze.video_analyzer.VideoFileClip') as mock_cls:
        mock_clip = MagicMock()
        mock_clip.__enter__.return_value = mock_clip
        mock_clip.__exit__.return_value = None
        mock_clip.duration = 8.0
        mock_clip.fps = 25.0
        mock_clip.w = 1920
        mock_clip.h = 1080
        mock_clip.audio = None
        mock_cls.return_value = mock_clip

        analyzer = VideoAnalyzer()
        results = analyzer.analyze_directory(str(tmp_path))

        assert len(results) == 2
        assert all(isinstance(r, VideoAnalysisResult) for r in results)
        assert all(r.file_type == "video-only" for r in results)


def test_analyze_directory_with_transcription(tmp_path, mock_video_clip, mock_whisper_model):
    """Test directory analysis with transcription enabled."""
    v1 = tmp_path / "video1.mp4"
    v2 = tmp_path / "video2.mp4"
    v1.touch()
    v2.touch()

    analyzer = VideoAnalyzer(whisper_model="tiny")
    results = analyzer.analyze_directory(str(tmp_path), transcribe=True)

    assert len(results) == 2
    assert all(r.transcript is not None for r in results)
    assert all(r.transcript_language == "en" for r in results)


def test_analyze_directory_invalid_path(analyzer):
    """Invalid directory path should raise ValueError."""
    with pytest.raises(ValueError):
        analyzer.analyze_directory("nonexistent_dir")


# ----------------------------
# Tests for metrics calculation
# ----------------------------

def test_calculate_collection_metrics_empty(analyzer):
    """Metrics should handle empty result list."""
    metrics = analyzer.calculate_collection_metrics([])

    assert isinstance(metrics, VideoCollectionMetrics)
    assert metrics.total_videos == 0
    assert metrics.total_duration == 0.0
    assert metrics.average_fps == 0.0
    assert metrics.resolutions == []
    assert metrics.formats == []
    assert metrics.audio_videos == 0
    assert metrics.video_only_files == 0
    assert metrics.transcribed_videos == 0


def test_calculate_collection_metrics(analyzer):
    """Validate correct aggregation of multiple video results."""
    results = [
        VideoAnalysisResult(
            file_path="video1.mp4",
            duration_seconds=10.0,
            resolution="1920x1080",
            frame_rate=30.0,
            total_frames=300,
            has_audio=True,
            file_type="video-with-audio",
            format="mp4",
            transcript="Test transcript 1",
            transcript_language="en"
        ),
        VideoAnalysisResult(
            file_path="video2.mov",
            duration_seconds=20.0,
            resolution="1280x720",
            frame_rate=60.0,
            total_frames=1200,
            has_audio=False,
            file_type="video-only",
            format="mov"
        )
    ]

    metrics = analyzer.calculate_collection_metrics(results)

    assert metrics.total_videos == 2
    assert metrics.total_duration == 30.0
    assert metrics.average_fps == 45.0
    assert set(metrics.resolutions) == {"1920x1080", "1280x720"}
    assert set(metrics.formats) == {"mp4", "mov"}
    assert metrics.audio_videos == 1
    assert metrics.video_only_files == 1
    assert metrics.transcribed_videos == 1


# ----------------------------
# Tests for JSON export
# ----------------------------

def test_save_to_json(tmp_path, analyzer):
    """Test saving results to JSON file."""
    results = [
        VideoAnalysisResult(
            file_path="video.mp4",
            duration_seconds=10.0,
            resolution="1920x1080",
            frame_rate=30.0,
            total_frames=300,
            has_audio=True,
            file_type="video-with-audio",
            format="mp4"
        )
    ]

    output_path = tmp_path / "output.json"
    analyzer.save_to_json(results, output_path)

    assert output_path.exists()
    import json
    with open(output_path, 'r') as f:
        data = json.load(f)
    
    assert len(data) == 1
    assert data[0]["file_path"] == "video.mp4"
    assert data[0]["duration_seconds"] == 10.0


def test_save_to_json_with_separate_transcripts(tmp_path, analyzer):
    """Test saving transcripts to separate file."""
    results = [
        VideoAnalysisResult(
            file_path="video.mp4",
            duration_seconds=10.0,
            resolution="1920x1080",
            frame_rate=30.0,
            total_frames=300,
            has_audio=True,
            file_type="video-with-audio",
            format="mp4",
            transcript="This is a transcript",
            transcript_language="en"
        )
    ]

    output_path = tmp_path / "output.json"
    analyzer.save_to_json(results, output_path, separate_transcripts=True)

    # Check main file exists
    assert output_path.exists()
    
    # Check transcript file exists
    transcript_path = tmp_path / "output_transcripts.json"
    assert transcript_path.exists()
    
    import json
    with open(transcript_path, 'r') as f:
        transcripts = json.load(f)
    
    assert "video.mp4" in transcripts
    assert transcripts["video.mp4"]["transcript"] == "This is a transcript"
    assert transcripts["video.mp4"]["language"] == "en"


# ----------------------------
# Integration: directory + metrics together
# ----------------------------

def test_directory_and_metrics_integration(tmp_path):
    """Integration test for directory analysis + metrics."""
    file1 = tmp_path / "clip1.mp4"
    file2 = tmp_path / "clip2.mp4"
    file1.touch()
    file2.touch()

    with patch('analyze.video_analyzer.VideoFileClip') as mock_cls:
        mock_clip = MagicMock()
        mock_clip.__enter__.return_value = mock_clip
        mock_clip.__exit__.return_value = None
        mock_clip.duration = 4.0
        mock_clip.fps = 24.0
        mock_clip.w = 1280
        mock_clip.h = 720
        mock_clip.audio = MagicMock()
        mock_cls.return_value = mock_clip

        analyzer = VideoAnalyzer()
        results = analyzer.analyze_directory(str(tmp_path))
        metrics = analyzer.calculate_collection_metrics(results)

        assert metrics.total_videos == 2
        assert metrics.audio_videos == 2
        assert metrics.video_only_files == 0
        assert "1280x720" in metrics.resolutions
        assert metrics.average_fps == 24.0
        assert metrics.transcribed_videos == 0  # No transcription was requested