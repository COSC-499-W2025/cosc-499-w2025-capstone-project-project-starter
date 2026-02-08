#!/usr/bin/env python3
"""
Test script for enhanced image processor with detailed content analysis.
"""

import json
import logging
from pathlib import Path
from src.image_processor import ImageProcessor


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def print_analysis_summary(analysis: dict):
    """Print a human-readable summary of the image analysis."""
    print("\n" + "="*80)
    print(f"IMAGE ANALYSIS: {analysis['file_name']}")
    print("="*80)
    
  
    print("\n📋 CONTENT CLASSIFICATION:")
    content = analysis.get('content_classification', {})
    print(f"  Type: {content.get('primary_type', 'Unknown')}")
    print(f"  Description: {content.get('description', 'N/A')}")
    print(f"  Confidence: {content.get('confidence', 'N/A')}")
    
    # Key Features
    print("\n🔑 KEY FEATURES:")
    key_features = analysis.get('key_features', {})
    for feature in key_features.get('key_features', []):
        print(f"  • {feature}")
    
    # Face Detection
    print("\n👤 FACE DETECTION:")
    faces = analysis.get('face_detection', {})
    print(f"  {faces.get('description', 'N/A')}")
    
    # Text Extraction
    print("\n📝 TEXT EXTRACTION:")
    text = analysis.get('text_extraction', {})
    print(f"  {text.get('description', 'N/A')}")
    if text.get('has_text') and text.get('text_content'):
        print(f"  Preview: {text.get('text_content', '')[:200]}...")
    
    # Shape Detection
    print("\n🔷 SHAPE DETECTION:")
    shapes = analysis.get('shape_detection', {})
    print(f"  {shapes.get('description', 'N/A')}")
    
    # Edge Detection
    print("\n🔲 EDGE DETECTION:")
    edges = analysis.get('edge_detection', {})
    print(f"  {edges.get('description', 'N/A')}")
    
    # Texture Analysis
    print("\n🎨 TEXTURE ANALYSIS:")
    texture = analysis.get('texture_analysis', {})
    print(f"  {texture.get('description', 'N/A')}")
    
    # Pattern Detection
    print("\n🔍 PATTERN DETECTION:")
    patterns = analysis.get('pattern_detection', {})
    print(f"  {patterns.get('description', 'N/A')}")
    if patterns.get('has_codes'):
        for code in patterns.get('codes', []):
            print(f"    - {code.get('type')}: {code.get('data')}")
    
    # Basic Metrics
    print("\n📊 BASIC METRICS:")
    resolution = analysis.get('resolution', {})
    print(f"  Resolution: {resolution.get('width')}x{resolution.get('height')} pixels")
    
    aspect = analysis.get('aspect_ratio', {})
    print(f"  Aspect Ratio: {aspect.get('ratio_string')} ({aspect.get('decimal')})")
    
    brightness = analysis.get('brightness', {})
    print(f"  Brightness: {brightness.get('brightness_percentage')}%")
    
    dominant = analysis.get('dominant_color', {}).get('most_dominant', {})
    if dominant:
        print(f"  Dominant Color: {dominant.get('hex')} ({dominant.get('percentage')}%)")
    
    print("\n" + "="*80 + "\n")


def main():
    """Main test function."""
    print("Enhanced Image Processor Test")
    print("="*80)
    
    
    processor = ImageProcessor()
    
   
    print("\nEnter the path to an image file (or press Enter to skip):")
    image_path = input("> ").strip()
    
    if not image_path:
        print("\nNo image path provided. Please provide an image to analyze.")
        print("\nExample usage:")
        print("  python test_enhanced_processor.py")
        print("\nThen enter the path to an image file when prompted.")
        print("\nThe processor can analyze:")
        print("  • Portraits and group photos (face detection)")
        print("  • Documents and text images (OCR)")
        print("  • Diagrams and illustrations (shape detection)")
        print("  • Screenshots and UI captures")
        print("  • QR codes and barcodes")
        print("  • General images with detailed texture and edge analysis")
        return
    
   
    if not Path(image_path).exists():
        print(f"\n❌ Error: File not found: {image_path}")
        return
    
 
    print(f"\n🔍 Analyzing image: {image_path}")
    print("This may take a moment...\n")
    
    try:
        analysis = processor.analyze_image(image_path)
        
       
        print_analysis_summary(analysis)
        
       
        output_file = Path(image_path).stem + "_analysis.json"
        with open(output_file, 'w') as f:
            json.dump(analysis, f, indent=2)
        print(f"✅ Full analysis saved to: {output_file}")
        
    except Exception as e:
        print(f"\n❌ Error analyzing image: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
