"""
Example usage of the ImageProcessor module.

This script demonstrates how to use the ImageProcessor to analyze
PNG and JPEG images and extract various metrics.
"""

import json
from pathlib import Path
from image_processor import ImageProcessor


def main():
    """Demonstrate image processor usage."""
    
    # Initialize the processor
    processor = ImageProcessor()
    
    print("=" * 60)
    print("Image Processor Demo")
    print("=" * 60)
    
    # Example 1: Analyze a single image
    print("\n1. Analyzing a single image:")
    print("-" * 60)
    
    # Replace with your actual image path
    image_path = "path/to/your/image.jpg"
    
    if Path(image_path).exists():
        try:
            result = processor.analyze_image(image_path)
            
            # Print key metrics
            print(f"File: {result['file_name']}")
            print(f"Resolution: {result['resolution']['width']}x{result['resolution']['height']}")
            print(f"Aspect Ratio: {result['aspect_ratio']['ratio_string']}")
            print(f"Format: {result['format']['format']}")
            print(f"File Size: {result['file_stats']['size_kb']} KB")
            print(f"Average Brightness: {result['brightness']['brightness_percentage']}%")
            print(f"Average Color (Hex): {result['average_color']['average_hex']}")
            
            if result['dominant_color']['most_dominant']:
                dominant = result['dominant_color']['most_dominant']
                print(f"Dominant Color: {dominant['hex']} ({dominant['percentage']}%)")
            
            if result['exif_metadata']['has_exif']:
                print(f"Camera: {result['exif_metadata']['camera_make']} {result['exif_metadata']['camera_model']}")
            
            print(f"Was Edited: {result['edit_frequency']['was_edited']}")
            
            # Save full result to JSON
            output_path = "image_analysis_result.json"
            with open(output_path, 'w') as f:
                json.dump(result, f, indent=2)
            print(f"\nFull analysis saved to: {output_path}")
            
        except Exception as e:
            print(f"Error analyzing image: {e}")
    else:
        print(f"Image not found: {image_path}")
        print("Please update the image_path variable with a valid image file.")
    
    # Example 2: Batch analyze multiple images
    print("\n\n2. Batch analyzing multiple images:")
    print("-" * 60)
    
    image_paths = [
        "path/to/image1.jpg",
        "path/to/image2.png",
        "path/to/image3.jpg"
    ]
    
    # Filter to only existing files
    existing_paths = [p for p in image_paths if Path(p).exists()]
    
    if existing_paths:
        results = processor.batch_analyze(existing_paths)
        
        for i, result in enumerate(results, 1):
            if 'error' not in result:
                print(f"\nImage {i}: {result['file_name']}")
                print(f"  Resolution: {result['resolution']['width']}x{result['resolution']['height']}")
                print(f"  Size: {result['file_stats']['size_kb']} KB")
                print(f"  Format: {result['format']['format']}")
            else:
                print(f"\nImage {i}: Error - {result['error']}")
        
        # Save batch results
        output_path = "batch_analysis_results.json"
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2)
        print(f"\nBatch analysis saved to: {output_path}")
    else:
        print("No valid image files found.")
        print("Please update the image_paths list with valid image files.")
    
    # Example 3: Check if a file format is supported
    print("\n\n3. Checking file format support:")
    print("-" * 60)
    
    test_files = [
        "image.png",
        "photo.jpg",
        "picture.jpeg",
        "document.pdf",
        "video.mp4"
    ]
    
    for file in test_files:
        supported = processor.is_supported_format(file)
        status = "✓ Supported" if supported else "✗ Not supported"
        print(f"{file}: {status}")
    
    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
