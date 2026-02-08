"""
Tests for image processor functionality.

"""

import json
import pytest
import os
import time
from datetime import datetime
from pathlib import Path
from PIL import Image
import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.image_processor import ImageProcessor


@pytest.fixture
def processor():
    """Create a fresh ImageProcessor for each test."""
    return ImageProcessor()


@pytest.fixture
def sample_png(tmp_path):
    """Create a sample PNG image for testing."""
    img_path = tmp_path / "test_image.png"
    
    
    img = Image.new('RGB', (100, 50))
    pixels = img.load()
    
    for x in range(100):
        for y in range(50):
          
            r = int((x / 100) * 255)
            g = int((y / 50) * 255)
            b = 128
            pixels[x, y] = (r, g, b)
    
    img.save(img_path, 'PNG')
    return str(img_path)


@pytest.fixture
def sample_jpeg(tmp_path):
    """Create a sample JPEG image for testing."""
    img_path = tmp_path / "test_image.jpg"
    
    
    img = Image.new('RGB', (200, 100), color=(255, 0, 0))  # Red image
    img.save(img_path, 'JPEG')
    return str(img_path)


@pytest.fixture
def sample_grayscale(tmp_path):
    """Create a grayscale image for testing."""
    img_path = tmp_path / "test_gray.png"
    
    
    img = Image.new('L', (50, 50), color=128)  # Mid-gray
    img.save(img_path, 'PNG')
    return str(img_path)


@pytest.fixture
def sample_with_exif(tmp_path):
    """Create a JPEG image with EXIF data."""
    img_path = tmp_path / "test_exif.jpg"
    
    
    img = Image.new('RGB', (100, 100), color=(0, 255, 0))  # Green image
    
    
    exif_dict = {
        271: "Test Camera Make",  # Make
        272: "Test Camera Model",  # Model
    }
    
    img.save(img_path, 'JPEG', exif=img.info.get('exif', b''))
    return str(img_path)


class TestImageProcessor:
    """Test cases for ImageProcessor class."""
    
    def test_initialization(self, processor):
        """Test processor initialization."""
        assert processor is not None
        assert processor.supported_formats == {'.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG'}
    
    def test_is_supported_format(self, processor):
        """Test format validation."""
        assert processor.is_supported_format("image.png")
        assert processor.is_supported_format("image.jpg")
        assert processor.is_supported_format("image.jpeg")
        assert processor.is_supported_format("IMAGE.PNG")
        assert processor.is_supported_format("IMAGE.JPG")
        assert not processor.is_supported_format("image.gif")
        assert not processor.is_supported_format("image.bmp")
        assert not processor.is_supported_format("image.txt")
    
    def test_get_resolution(self, processor, sample_png):
        """Test resolution extraction."""
        with Image.open(sample_png) as img:
            resolution = processor.get_resolution(img)
        
        assert resolution["width"] == 100
        assert resolution["height"] == 50
        assert resolution["total_pixels"] == 5000
    
    def test_get_aspect_ratio(self, processor):
        """Test aspect ratio calculation."""
        ratio = processor.get_aspect_ratio(100, 50)
        
        assert ratio["ratio"] == 2.0
        assert ratio["ratio_string"] == "2:1"
        assert ratio["decimal"] == 2.0
        
        
        ratio_16_9 = processor.get_aspect_ratio(1920, 1080)
        assert ratio_16_9["ratio_string"] == "16:9"
        
       
        ratio_square = processor.get_aspect_ratio(100, 100)
        assert ratio_square["ratio_string"] == "1:1"
        assert ratio_square["decimal"] == 1.0
    
    def test_get_aspect_ratio_zero_height(self, processor):
        """Test aspect ratio with zero height."""
        ratio = processor.get_aspect_ratio(100, 0)
        assert ratio["ratio"] == 0
        assert ratio["decimal"] == 0
    
    def test_get_file_format_png(self, processor, sample_png):
        """Test file format extraction for PNG."""
        with Image.open(sample_png) as img:
            format_info = processor.get_file_format(img, sample_png)
        
        assert format_info["format"] == "PNG"
        assert format_info["mode"] == "RGB"
        assert format_info["extension"] == ".png"
    
    def test_get_file_format_jpeg(self, processor, sample_jpeg):
        """Test file format extraction for JPEG."""
        with Image.open(sample_jpeg) as img:
            format_info = processor.get_file_format(img, sample_jpeg)
        
        assert format_info["format"] == "JPEG"
        assert format_info["mode"] == "RGB"
        assert format_info["extension"] == ".jpg"
    
    def test_get_file_stats(self, processor, sample_png):
        """Test file statistics extraction."""
        stats = processor.get_file_stats(sample_png)
        
        assert "size_bytes" in stats
        assert "size_kb" in stats
        assert "size_mb" in stats
        assert stats["size_bytes"] > 0
        assert stats["size_kb"] > 0
        
        assert "created_timestamp" in stats
        assert "created_datetime" in stats
        assert "modified_timestamp" in stats
        assert "modified_datetime" in stats
        assert "accessed_timestamp" in stats
        assert "accessed_datetime" in stats
        
        
        datetime.fromisoformat(stats["created_datetime"])
        datetime.fromisoformat(stats["modified_datetime"])
    
    def test_get_average_brightness(self, processor, sample_grayscale):
        """Test brightness calculation."""
        with Image.open(sample_grayscale) as img:
            brightness = processor.get_average_brightness(img)
        
        assert "average_brightness" in brightness
        assert "brightness_percentage" in brightness
        assert "min_brightness" in brightness
        assert "max_brightness" in brightness
        
        
        assert 45 <= brightness["brightness_percentage"] <= 55
        assert brightness["min_brightness"] == 128
        assert brightness["max_brightness"] == 128
    
    def test_get_average_color(self, processor, sample_jpeg):
        """Test average color calculation."""
        with Image.open(sample_jpeg) as img:
            avg_color = processor.get_average_color(img)
        
        assert "average_rgb" in avg_color
        assert "average_hex" in avg_color
        
        rgb = avg_color["average_rgb"]
        assert "r" in rgb
        assert "g" in rgb
        assert "b" in rgb
        
        
        assert rgb["r"] > 200
        assert rgb["g"] < 50
        assert rgb["b"] < 50
        
        
        assert avg_color["average_hex"].startswith("#")
        assert len(avg_color["average_hex"]) == 7
    
    def test_get_dominant_color(self, processor, sample_jpeg):
        """Test dominant color extraction."""
        with Image.open(sample_jpeg) as img:
            dominant = processor.get_dominant_color(img, num_colors=3)
        
        assert "dominant_colors" in dominant
        assert "most_dominant" in dominant
        assert len(dominant["dominant_colors"]) <= 3
        
        if dominant["dominant_colors"]:
            color = dominant["dominant_colors"][0]
            assert "rgb" in color
            assert "hex" in color
            assert "frequency" in color
            assert "percentage" in color
            
            assert color["hex"].startswith("#")
            assert 0 <= color["percentage"] <= 100
    
    def test_get_exif_metadata_no_exif(self, processor, sample_png):
        """Test EXIF extraction when no EXIF data present."""
        with Image.open(sample_png) as img:
            exif = processor.get_exif_metadata(img)
        
        assert "has_exif" in exif
        assert exif["has_exif"] is False
        assert "data" in exif
    
    def test_calculate_edit_frequency(self, processor, sample_png):
        """Test edit frequency calculation."""
        edit_freq = processor.calculate_edit_frequency(sample_png)
        
        assert "was_edited" in edit_freq
        assert "created" in edit_freq
        assert "last_modified" in edit_freq
        assert "days_since_creation" in edit_freq
        assert "time_between_create_modify_seconds" in edit_freq
        
        
        datetime.fromisoformat(edit_freq["created"])
        datetime.fromisoformat(edit_freq["last_modified"])
        
        
        assert edit_freq["days_since_creation"] >= 0
    
    def test_calculate_edit_frequency_modified_file(self, processor, tmp_path):
        """Test edit frequency with modified file."""
        img_path = tmp_path / "test_modified.png"
        
       
        img = Image.new('RGB', (50, 50), color=(0, 0, 255))
        img.save(img_path, 'PNG')
        
        
        time.sleep(0.1)
        os.utime(img_path, None)  
        
        edit_freq = processor.calculate_edit_frequency(str(img_path))
        
       
        assert edit_freq["time_between_create_modify_seconds"] >= 0
    
    def test_analyze_image_complete(self, processor, sample_png):
        """Test complete image analysis."""
        result = processor.analyze_image(sample_png)
        
        
        expected_keys = [
            "file_path", "file_name", "resolution", "aspect_ratio",
            "format", "file_stats", "brightness", "average_color",
            "dominant_color", "exif_metadata", "edit_frequency",
            "analysis_timestamp"
        ]
        
        for key in expected_keys:
            assert key in result, f"Missing key: {key}"
        
       
        assert result["resolution"]["width"] == 100
        assert result["resolution"]["height"] == 50
        
       
        assert result["aspect_ratio"]["ratio_string"] == "2:1"
        
        
        assert result["format"]["format"] == "PNG"
        
        
        datetime.fromisoformat(result["analysis_timestamp"])
    
    def test_analyze_image_jpeg(self, processor, sample_jpeg):
        """Test analysis of JPEG image."""
        result = processor.analyze_image(sample_jpeg)
        
        assert result["resolution"]["width"] == 200
        assert result["resolution"]["height"] == 100
        assert result["format"]["format"] == "JPEG"
        assert result["format"]["extension"] == ".jpg"
    
    def test_analyze_image_file_not_found(self, processor):
        """Test error handling for non-existent file."""
        with pytest.raises(FileNotFoundError):
            processor.analyze_image("/nonexistent/path/image.png")
    
    def test_analyze_image_unsupported_format(self, processor, tmp_path):
        """Test error handling for unsupported format."""
        txt_file = tmp_path / "test.txt"
        txt_file.write_text("not an image")
        
        with pytest.raises(ValueError):
            processor.analyze_image(str(txt_file))
    
    def test_batch_analyze(self, processor, sample_png, sample_jpeg):
        """Test batch analysis of multiple images."""
        results = processor.batch_analyze([sample_png, sample_jpeg])
        
        assert len(results) == 2
        
        
        assert results[0]["format"]["format"] == "PNG"
        assert results[0]["resolution"]["width"] == 100
        
        
        assert results[1]["format"]["format"] == "JPEG"
        assert results[1]["resolution"]["width"] == 200
    
    def test_batch_analyze_with_errors(self, processor, sample_png):
        """Test batch analysis with some invalid files."""
        results = processor.batch_analyze([
            sample_png,
            "/nonexistent/image.png"
        ])
        
        assert len(results) == 2
        
        
        assert "error" not in results[0]
        assert results[0]["format"]["format"] == "PNG"
        
        
        assert "error" in results[1]
        assert results[1]["file_path"] == "/nonexistent/image.png"
    
    def test_batch_analyze_empty_list(self, processor):
        """Test batch analysis with empty list."""
        results = processor.batch_analyze([])
        assert results == []
    
    def test_different_aspect_ratios(self, processor, tmp_path):
        """Test various aspect ratios."""
        test_cases = [
            (1920, 1080, "16:9"),
            (1280, 720, "16:9"),
            (800, 600, "4:3"),
            (1024, 768, "4:3"),
            (100, 100, "1:1"),
        ]
        
        for width, height, expected_ratio in test_cases:
            img_path = tmp_path / f"test_{width}x{height}.png"
            img = Image.new('RGB', (width, height))
            img.save(img_path, 'PNG')
            
            result = processor.analyze_image(str(img_path))
            assert result["aspect_ratio"]["ratio_string"] == expected_ratio
    
    def test_brightness_extremes(self, processor, tmp_path):
        """Test brightness calculation for black and white images."""
       
        black_path = tmp_path / "black.png"
        black_img = Image.new('RGB', (50, 50), color=(0, 0, 0))
        black_img.save(black_path, 'PNG')
        
        with Image.open(black_path) as img:
            brightness = processor.get_average_brightness(img)
        
        assert brightness["average_brightness"] < 10
        assert brightness["brightness_percentage"] < 5
        
        
        white_path = tmp_path / "white.png"
        white_img = Image.new('RGB', (50, 50), color=(255, 255, 255))
        white_img.save(white_path, 'PNG')
        
        with Image.open(white_path) as img:
            brightness = processor.get_average_brightness(img)
        
        assert brightness["average_brightness"] > 245
        assert brightness["brightness_percentage"] > 95
    
    def test_color_modes(self, processor, tmp_path):
        """Test handling of different color modes."""
        
        rgba_path = tmp_path / "rgba.png"
        rgba_img = Image.new('RGBA', (50, 50), color=(255, 0, 0, 128))
        rgba_img.save(rgba_path, 'PNG')
        
        result = processor.analyze_image(str(rgba_path))
        assert result["format"]["mode"] == "RGBA"
        
        
        gray_path = tmp_path / "gray.png"
        gray_img = Image.new('L', (50, 50), color=128)
        gray_img.save(gray_path, 'PNG')
        
        result = processor.analyze_image(str(gray_path))
        assert result["format"]["mode"] == "L"
