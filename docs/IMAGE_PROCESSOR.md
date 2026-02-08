# Image Processor Documentation

## Overview

The `ImageProcessor` module provides comprehensive analysis of PNG and JPEG image files, extracting various metrics including resolution, aspect ratio, file format, file size, timestamps, color analysis, EXIF metadata, and edit frequency.

## Features

### Supported Metrics

1. **Resolution** - Width × Height in pixels
2. **Aspect Ratio** - Calculated ratio and simplified format (e.g., 16:9)
3. **File Format** - Format type, color mode, and file extension
4. **File Statistics** - Size in bytes/KB/MB and timestamps (created, modified, accessed)
5. **Brightness Analysis** - Average brightness, min/max values, and percentage
6. **Color Analysis** - Average RGB values and hex color code
7. **Dominant Colors** - Top N most frequent colors with percentages
8. **EXIF Metadata** - Camera make/model, date taken, GPS data (if available)
9. **Edit Frequency** - Whether file was edited and time between creation/modification

## Installation

Install the required dependencies:

```bash
pip install Pillow numpy
```

Or install from requirements.txt:

```bash
pip install -r requirements.txt
```

## Usage

### Basic Usage

```python
from src.image_processor import ImageProcessor

# Initialize the processor
processor = ImageProcessor()

# Analyze a single image
result = processor.analyze_image("path/to/image.jpg")

# Access metrics
print(f"Resolution: {result['resolution']['width']}x{result['resolution']['height']}")
print(f"Aspect Ratio: {result['aspect_ratio']['ratio_string']}")
print(f"File Size: {result['file_stats']['size_kb']} KB")
print(f"Average Brightness: {result['brightness']['brightness_percentage']}%")
```

### Batch Analysis

```python
# Analyze multiple images
image_paths = ["image1.jpg", "image2.png", "image3.jpeg"]
results = processor.batch_analyze(image_paths)

for result in results:
    if 'error' not in result:
        print(f"{result['file_name']}: {result['resolution']['width']}x{result['resolution']['height']}")
```

### Check Format Support

```python
# Check if a file format is supported
is_supported = processor.is_supported_format("image.png")  # Returns True
is_supported = processor.is_supported_format("video.mp4")  # Returns False
```

## API Reference

### ImageProcessor Class

#### Methods

##### `analyze_image(file_path: str) -> Dict[str, Any]`

Performs comprehensive analysis of a single image file.

**Parameters:**
- `file_path` (str): Path to the image file

**Returns:**
- Dictionary containing all metrics

**Raises:**
- `FileNotFoundError`: If the image file doesn't exist
- `ValueError`: If the file format is not supported

**Example:**
```python
result = processor.analyze_image("photo.jpg")
```

##### `batch_analyze(file_paths: List[str]) -> List[Dict[str, Any]]`

Analyzes multiple images at once.

**Parameters:**
- `file_paths` (List[str]): List of paths to image files

**Returns:**
- List of analysis results (includes error info for failed analyses)

**Example:**
```python
results = processor.batch_analyze(["img1.jpg", "img2.png"])
```

##### `is_supported_format(file_path: str) -> bool`

Checks if a file format is supported.

**Parameters:**
- `file_path` (str): Path to the file

**Returns:**
- True if format is supported, False otherwise

**Example:**
```python
if processor.is_supported_format("image.png"):
    result = processor.analyze_image("image.png")
```

##### `get_resolution(image: Image.Image) -> Dict[str, int]`

Extracts resolution information from an image.

**Returns:**
```python
{
    "width": 1920,
    "height": 1080,
    "total_pixels": 2073600
}
```

##### `get_aspect_ratio(width: int, height: int) -> Dict[str, Any]`

Calculates aspect ratio.

**Returns:**
```python
{
    "ratio": 1.78,
    "ratio_string": "16:9",
    "decimal": 1.78
}
```

##### `get_file_format(image: Image.Image, file_path: str) -> Dict[str, str]`

Gets file format information.

**Returns:**
```python
{
    "format": "JPEG",
    "mode": "RGB",
    "extension": ".jpg"
}
```

##### `get_file_stats(file_path: str) -> Dict[str, Any]`

Gets file size and timestamp information.

**Returns:**
```python
{
    "size_bytes": 1048576,
    "size_kb": 1024.0,
    "size_mb": 1.0,
    "created_timestamp": 1234567890.0,
    "created_datetime": "2023-01-01T12:00:00",
    "modified_timestamp": 1234567890.0,
    "modified_datetime": "2023-01-01T12:00:00",
    "accessed_timestamp": 1234567890.0,
    "accessed_datetime": "2023-01-01T12:00:00"
}
```

##### `get_average_brightness(image: Image.Image) -> Dict[str, float]`

Calculates average brightness.

**Returns:**
```python
{
    "average_brightness": 128.5,
    "brightness_percentage": 50.4,
    "min_brightness": 0,
    "max_brightness": 255
}
```

##### `get_average_color(image: Image.Image) -> Dict[str, Any]`

Calculates average color values.

**Returns:**
```python
{
    "average_rgb": {
        "r": 128.5,
        "g": 64.2,
        "b": 200.1
    },
    "average_hex": "#8040c8"
}
```

##### `get_dominant_color(image: Image.Image, num_colors: int = 5) -> Dict[str, Any]`

Finds dominant colors in the image.

**Returns:**
```python
{
    "dominant_colors": [
        {
            "rgb": {"r": 255, "g": 0, "b": 0},
            "hex": "#ff0000",
            "frequency": 12500,
            "percentage": 55.5
        }
    ],
    "most_dominant": {...}
}
```

##### `get_exif_metadata(image: Image.Image) -> Dict[str, Any]`

Extracts EXIF metadata.

**Returns:**
```python
{
    "has_exif": True,
    "data": {...},
    "camera_make": "Canon",
    "camera_model": "EOS 5D",
    "datetime_original": "2023:01:01 12:00:00",
    "has_gps": True
}
```

##### `calculate_edit_frequency(file_path: str) -> Dict[str, Any]`

Calculates edit frequency based on timestamps.

**Returns:**
```python
{
    "was_edited": True,
    "created": "2023-01-01T12:00:00",
    "last_modified": "2023-01-02T12:00:00",
    "days_since_creation": 1.0,
    "time_between_create_modify_seconds": 86400.0
}
```

## Output Format

The `analyze_image()` method returns a comprehensive dictionary with the following structure:

```python
{
    "file_path": "/absolute/path/to/image.jpg",
    "file_name": "image.jpg",
    "resolution": {
        "width": 1920,
        "height": 1080,
        "total_pixels": 2073600
    },
    "aspect_ratio": {
        "ratio": 1.78,
        "ratio_string": "16:9",
        "decimal": 1.78
    },
    "format": {
        "format": "JPEG",
        "mode": "RGB",
        "extension": ".jpg"
    },
    "file_stats": {
        "size_bytes": 1048576,
        "size_kb": 1024.0,
        "size_mb": 1.0,
        "created_datetime": "2023-01-01T12:00:00",
        "modified_datetime": "2023-01-01T12:00:00",
        ...
    },
    "brightness": {
        "average_brightness": 128.5,
        "brightness_percentage": 50.4,
        ...
    },
    "average_color": {
        "average_rgb": {"r": 128.5, "g": 64.2, "b": 200.1},
        "average_hex": "#8040c8"
    },
    "dominant_color": {
        "dominant_colors": [...],
        "most_dominant": {...}
    },
    "exif_metadata": {
        "has_exif": True,
        "camera_make": "Canon",
        ...
    },
    "edit_frequency": {
        "was_edited": True,
        "days_since_creation": 1.0,
        ...
    },
    "analysis_timestamp": "2023-01-01T12:00:00"
}
```

## Supported Formats

- PNG (.png, .PNG)
- JPEG (.jpg, .jpeg, .JPG, .JPEG)

## Error Handling

The processor includes comprehensive error handling:

- **FileNotFoundError**: Raised when the image file doesn't exist
- **ValueError**: Raised when the file format is not supported
- **Batch Analysis**: Errors are captured in the result dictionary with an "error" key

Example error handling:

```python
try:
    result = processor.analyze_image("image.jpg")
except FileNotFoundError:
    print("Image file not found")
except ValueError:
    print("Unsupported file format")
```

## Testing

Run the test suite:

```bash
# Run all image processor tests
python -m pytest tests/test_image_processor.py -v

# Run with coverage
python -m pytest tests/test_image_processor.py --cov=src.image_processor

# Run specific test
python -m pytest tests/test_image_processor.py::TestImageProcessor::test_analyze_image_complete -v
```

## Examples

### Example 1: Basic Image Analysis

```python
from src.image_processor import ImageProcessor

processor = ImageProcessor()
result = processor.analyze_image("photo.jpg")

print(f"Resolution: {result['resolution']['width']}x{result['resolution']['height']}")
print(f"File Size: {result['file_stats']['size_mb']} MB")
print(f"Dominant Color: {result['dominant_color']['most_dominant']['hex']}")
```

### Example 2: Batch Processing

```python
import os
from src.image_processor import ImageProcessor

processor = ImageProcessor()

# Get all images in a directory
image_dir = "path/to/images"
image_files = [
    os.path.join(image_dir, f) 
    for f in os.listdir(image_dir) 
    if processor.is_supported_format(f)
]

# Analyze all images
results = processor.batch_analyze(image_files)

# Print summary
for result in results:
    if 'error' not in result:
        print(f"{result['file_name']}: {result['resolution']['width']}x{result['resolution']['height']}")
```

### Example 3: Filtering by Metrics

```python
from src.image_processor import ImageProcessor

processor = ImageProcessor()

# Analyze multiple images
results = processor.batch_analyze(["img1.jpg", "img2.jpg", "img3.jpg"])

# Filter high-resolution images
high_res = [
    r for r in results 
    if 'error' not in r and r['resolution']['total_pixels'] > 2000000
]

# Filter bright images
bright_images = [
    r for r in results 
    if 'error' not in r and r['brightness']['brightness_percentage'] > 70
]

print(f"Found {len(high_res)} high-resolution images")
print(f"Found {len(bright_images)} bright images")
```

## Performance Considerations

- **Large Images**: Processing very large images may take longer. Consider resizing for faster analysis.
- **Batch Processing**: Use `batch_analyze()` for multiple images to benefit from optimized processing.
- **Dominant Color Calculation**: This operation is optimized by resizing the image to 150x150 pixels internally.

## Dependencies

- **Pillow**: Image loading and basic operations
- **NumPy**: Numerical operations for color and brightness calculations
- **Python Standard Library**: File operations, datetime handling

## License

This module is part of the capstone project and follows the project's license.
