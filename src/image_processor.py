"""
Image processor for analyzing PNG/JPEG files and extracting metrics.

"""

import os
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from collections import Counter

import numpy as np
from PIL import Image
from PIL.ExifTags import TAGS, GPSTAGS
import cv2
import pytesseract
from pyzbar import pyzbar
from skimage import feature, filters, measure
from skimage.color import rgb2gray
from skimage.feature import graycomatrix, graycoprops


class ImageProcessor:
    """Processes and analyzes image files to extract comprehensive metrics."""

    def __init__(self):
        """Initialize the image processor."""
        self.logger = logging.getLogger(__name__)
        self.supported_formats = {'.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG'}

    def is_supported_format(self, file_path: str) -> bool:
        """
        Check if the file format is supported.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            True if format is supported, False otherwise
        """
        return Path(file_path).suffix in self.supported_formats

    def get_resolution(self, image: Image.Image) -> Dict[str, int]:
        """
        Get image resolution (width × height).
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with width and height
        """
        width, height = image.size
        return {
            "width": width,
            "height": height,
            "total_pixels": width * height
        }

    def get_aspect_ratio(self, width: int, height: int) -> Dict[str, Any]:
        """
        Calculate aspect ratio.
        
        Args:
            width: Image width
            height: Image height
            
        Returns:
            Dictionary with aspect ratio information
        """
        if height == 0:
            return {"ratio": 0, "ratio_string": "0:0", "decimal": 0}
        
        ratio = width / height
        
        
        from math import gcd
        divisor = gcd(width, height)
        simplified_width = width // divisor
        simplified_height = height // divisor
        
        return {
            "ratio": ratio,
            "ratio_string": f"{simplified_width}:{simplified_height}",
            "decimal": round(ratio, 2)
        }

    def get_file_format(self, image: Image.Image, file_path: str) -> Dict[str, str]:
        """
        Get file format information.
        
        Args:
            image: PIL Image object
            file_path: Path to the image file
            
        Returns:
            Dictionary with format information
        """
        return {
            "format": image.format or "UNKNOWN",
            "mode": image.mode,
            "extension": Path(file_path).suffix.lower()
        }

    def get_file_stats(self, file_path: str) -> Dict[str, Any]:
        """
        Get file size and timestamp information.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary with file statistics
        """
        stats = os.stat(file_path)
        
        return {
            "size_bytes": stats.st_size,
            "size_kb": round(stats.st_size / 1024, 2),
            "size_mb": round(stats.st_size / (1024 * 1024), 2),
            "created_timestamp": stats.st_ctime,
            "created_datetime": datetime.fromtimestamp(stats.st_ctime).isoformat(),
            "modified_timestamp": stats.st_mtime,
            "modified_datetime": datetime.fromtimestamp(stats.st_mtime).isoformat(),
            "accessed_timestamp": stats.st_atime,
            "accessed_datetime": datetime.fromtimestamp(stats.st_atime).isoformat()
        }

    def get_average_brightness(self, image: Image.Image) -> Dict[str, float]:
        """
        Calculate average brightness of the image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with brightness information
        """
        
        grayscale = image.convert('L')
        pixels = np.array(grayscale)
        
        avg_brightness = np.mean(pixels)
        
        return {
            "average_brightness": round(float(avg_brightness), 2),
            "brightness_percentage": round(float(avg_brightness) / 255 * 100, 2),
            "min_brightness": int(np.min(pixels)),
            "max_brightness": int(np.max(pixels))
        }

    def get_average_color(self, image: Image.Image) -> Dict[str, Any]:
        """
        Calculate average color values.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with average color information
        """
        
        rgb_image = image.convert('RGB')
        pixels = np.array(rgb_image)
        
        
        avg_r = np.mean(pixels[:, :, 0])
        avg_g = np.mean(pixels[:, :, 1])
        avg_b = np.mean(pixels[:, :, 2])
        
        return {
            "average_rgb": {
                "r": round(float(avg_r), 2),
                "g": round(float(avg_g), 2),
                "b": round(float(avg_b), 2)
            },
            "average_hex": f"#{int(avg_r):02x}{int(avg_g):02x}{int(avg_b):02x}"
        }

    def get_dominant_color(self, image: Image.Image, num_colors: int = 5) -> Dict[str, Any]:
        """
        Find dominant colors in the image.
        
        Args:
            image: PIL Image object
            num_colors: Number of dominant colors to return
            
        Returns:
            Dictionary with dominant color information
        """
        
        small_image = image.convert('RGB').resize((150, 150))
        pixels = np.array(small_image)
        
        
        pixels_list = pixels.reshape(-1, 3)
        
       
        pixel_tuples = [tuple(pixel) for pixel in pixels_list]
        
     
        color_counts = Counter(pixel_tuples)
        most_common = color_counts.most_common(num_colors)
        
        dominant_colors = []
        for color, count in most_common:
            dominant_colors.append({
                "rgb": {"r": color[0], "g": color[1], "b": color[2]},
                "hex": f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}",
                "frequency": count,
                "percentage": round(count / len(pixel_tuples) * 100, 2)
            })
        
        return {
            "dominant_colors": dominant_colors,
            "most_dominant": dominant_colors[0] if dominant_colors else None
        }

    def get_exif_metadata(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extract EXIF metadata from the image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with EXIF metadata
        """
        exif_data = {}
        
        try:
            exif = image._getexif()
            
            if exif is None:
                return {"has_exif": False, "data": {}}
            
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                
                
                if tag == "GPSInfo":
                    gps_data = {}
                    for gps_tag_id in value:
                        gps_tag = GPSTAGS.get(gps_tag_id, gps_tag_id)
                        gps_data[gps_tag] = value[gps_tag_id]
                    exif_data["GPSInfo"] = gps_data
                else:
                   
                    if isinstance(value, bytes):
                        try:
                            value = value.decode()
                        except:
                            value = str(value)
                    exif_data[tag] = value
            
            return {
                "has_exif": True,
                "data": exif_data,
                "camera_make": exif_data.get("Make", "Unknown"),
                "camera_model": exif_data.get("Model", "Unknown"),
                "datetime_original": exif_data.get("DateTimeOriginal", "Unknown"),
                "has_gps": "GPSInfo" in exif_data
            }
            
        except AttributeError:
            return {"has_exif": False, "data": {}}
        except Exception as e:
            self.logger.warning(f"Error extracting EXIF data: {e}")
            return {"has_exif": False, "error": str(e), "data": {}}

    def calculate_edit_frequency(self, file_path: str) -> Dict[str, Any]:
        """
        Calculate frequency of edits based on timestamps.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary with edit frequency information
        """
        stats = os.stat(file_path)
        
        created = datetime.fromtimestamp(stats.st_ctime)
        modified = datetime.fromtimestamp(stats.st_mtime)
        
        time_diff = modified - created
        days_since_creation = time_diff.total_seconds() / 86400
        
       
        was_edited = abs(stats.st_mtime - stats.st_ctime) > 1  # 1 second tolerance
        
        return {
            "was_edited": was_edited,
            "created": created.isoformat(),
            "last_modified": modified.isoformat(),
            "days_since_creation": round(days_since_creation, 2),
            "time_between_create_modify_seconds": round(time_diff.total_seconds(), 2)
        }

    def detect_edges(self, image: Image.Image) -> Dict[str, Any]:
        """
        Detect edges in the image using Canny edge detection.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with edge detection information
        """
        # Convert to OpenCV format
        img_array = np.array(image.convert('RGB'))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Apply Canny edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Calculate edge statistics
        edge_pixels = np.count_nonzero(edges)
        total_pixels = edges.size
        edge_percentage = (edge_pixels / total_pixels) * 100
        
        # Determine complexity based on edge density
        if edge_percentage < 5:
            complexity = "simple"
        elif edge_percentage < 15:
            complexity = "moderate"
        else:
            complexity = "complex"
        
        return {
            "edge_pixel_count": int(edge_pixels),
            "edge_percentage": round(edge_percentage, 2),
            "complexity": complexity,
            "description": f"Image has {complexity} edge structure with {round(edge_percentage, 1)}% edge pixels"
        }

    def detect_shapes(self, image: Image.Image) -> Dict[str, Any]:
        """
        Detect shapes and contours in the image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with shape detection information
        """
        # Convert to OpenCV format
        img_array = np.array(image.convert('RGB'))
        gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
        
        # Apply threshold
        _, thresh = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Analyze shapes
        shapes = []
        circles = 0
        rectangles = 0
        triangles = 0
        polygons = 0
        
        for contour in contours:
            # Filter small contours
            area = cv2.contourArea(contour)
            if area < 100:  # Ignore very small shapes
                continue
            
            # Approximate the contour
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.04 * perimeter, True)
            
            # Classify shape based on number of vertices
            vertices = len(approx)
            
            if vertices == 3:
                triangles += 1
                shape_type = "triangle"
            elif vertices == 4:
                rectangles += 1
                shape_type = "rectangle/square"
            elif vertices > 8:
                circles += 1
                shape_type = "circle/ellipse"
            else:
                polygons += 1
                shape_type = f"{vertices}-sided polygon"
            
            shapes.append({
                "type": shape_type,
                "vertices": vertices,
                "area": float(area)
            })
        
        # Generate description
        shape_desc = []
        if circles > 0:
            shape_desc.append(f"{circles} circular shape(s)")
        if rectangles > 0:
            shape_desc.append(f"{rectangles} rectangular shape(s)")
        if triangles > 0:
            shape_desc.append(f"{triangles} triangular shape(s)")
        if polygons > 0:
            shape_desc.append(f"{polygons} polygonal shape(s)")
        
        description = "Image contains " + ", ".join(shape_desc) if shape_desc else "No distinct geometric shapes detected"
        
        return {
            "total_shapes": len(shapes),
            "circles": circles,
            "rectangles": rectangles,
            "triangles": triangles,
            "polygons": polygons,
            "shapes_detail": shapes[:10],  # Limit to top 10 shapes
            "description": description
        }

    def extract_text(self, image: Image.Image) -> Dict[str, Any]:
        """
        Extract text from image using OCR.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with text extraction information
        """
        try:
            # Extract text using pytesseract
            text = pytesseract.image_to_string(image)
            
            # Get detailed data
            data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            # Filter out empty text
            words = [word for word in data['text'] if word.strip()]
            confidences = [conf for word, conf in zip(data['text'], data['conf']) if word.strip() and conf != -1]
            
            has_text = len(text.strip()) > 0
            avg_confidence = np.mean(confidences) if confidences else 0
            
            # Determine text content type
            text_type = "none"
            if has_text:
                if len(words) > 50:
                    text_type = "document/article"
                elif len(words) > 10:
                    text_type = "text-heavy"
                else:
                    text_type = "minimal text"
            
            return {
                "has_text": has_text,
                "text_content": text.strip()[:500],  
                "word_count": len(words),
                "average_confidence": round(float(avg_confidence), 2),
                "text_type": text_type,
                "description": f"Image contains {text_type}" if has_text else "No readable text detected"
            }
        except Exception as e:
            self.logger.warning(f"Error extracting text: {e}")
            return {
                "has_text": False,
                "error": str(e),
                "description": "Text extraction unavailable (tesseract may not be installed)"
            }

    def detect_faces(self, image: Image.Image) -> Dict[str, Any]:
        """
        Detect faces in the image using Haar Cascade.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with face detection information
        """
        try:
          
            img_array = np.array(image.convert('RGB'))
            gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
            
       
            face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
            
            face_details = []
            for (x, y, w, h) in faces:
                face_details.append({
                    "position": {"x": int(x), "y": int(y)},
                    "size": {"width": int(w), "height": int(h)},
                    "area": int(w * h)
                })
            
            has_faces = len(faces) > 0
            
          
            if has_faces:
                if len(faces) == 1:
                    description = "Image contains 1 detected face (portrait/person)"
                else:
                    description = f"Image contains {len(faces)} detected faces (group photo)"
            else:
                description = "No faces detected"
            
            return {
                "has_faces": has_faces,
                "face_count": len(faces),
                "faces": face_details,
                "description": description
            }
        except Exception as e:
            self.logger.warning(f"Error detecting faces: {e}")
            return {
                "has_faces": False,
                "face_count": 0,
                "error": str(e),
                "description": "Face detection unavailable"
            }

    def analyze_texture(self, image: Image.Image) -> Dict[str, Any]:
        """
        Analyze texture properties of the image.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with texture analysis information
        """
        
        gray = np.array(image.convert('L'))
        
       
        if gray.shape[0] > 512 or gray.shape[1] > 512:
            scale = 512 / max(gray.shape)
            new_shape = (int(gray.shape[1] * scale), int(gray.shape[0] * scale))
            gray = cv2.resize(gray, new_shape)
        
    
        glcm = graycomatrix(gray, distances=[1], angles=[0, np.pi/4, np.pi/2, 3*np.pi/4], 
                           levels=256, symmetric=True, normed=True)
        
      
        contrast = graycoprops(glcm, 'contrast')[0, 0]
        dissimilarity = graycoprops(glcm, 'dissimilarity')[0, 0]
        homogeneity = graycoprops(glcm, 'homogeneity')[0, 0]
        energy = graycoprops(glcm, 'energy')[0, 0]
        correlation = graycoprops(glcm, 'correlation')[0, 0]
        
       
        if homogeneity > 0.8:
            texture_type = "smooth/uniform"
        elif contrast > 100:
            texture_type = "rough/highly textured"
        elif energy > 0.5:
            texture_type = "repetitive pattern"
        else:
            texture_type = "varied/natural"
        
        return {
            "contrast": round(float(contrast), 2),
            "dissimilarity": round(float(dissimilarity), 2),
            "homogeneity": round(float(homogeneity), 2),
            "energy": round(float(energy), 2),
            "correlation": round(float(correlation), 2),
            "texture_type": texture_type,
            "description": f"Image has {texture_type} texture"
        }

    def detect_patterns(self, image: Image.Image) -> Dict[str, Any]:
        """
        Detect patterns like QR codes and barcodes.
        
        Args:
            image: PIL Image object
            
        Returns:
            Dictionary with pattern detection information
        """
        try:
            # Detect barcodes and QR codes
            barcodes = pyzbar.decode(image)
            
            detected_codes = []
            for barcode in barcodes:
                detected_codes.append({
                    "type": barcode.type,
                    "data": barcode.data.decode('utf-8'),
                    "position": {
                        "x": barcode.rect.left,
                        "y": barcode.rect.top,
                        "width": barcode.rect.width,
                        "height": barcode.rect.height
                    }
                })
            
            has_codes = len(detected_codes) > 0
            
           
            if has_codes:
                code_types = [code['type'] for code in detected_codes]
                description = f"Image contains {len(detected_codes)} barcode/QR code(s): {', '.join(code_types)}"
            else:
                description = "No barcodes or QR codes detected"
            
            return {
                "has_codes": has_codes,
                "code_count": len(detected_codes),
                "codes": detected_codes,
                "description": description
            }
        except Exception as e:
            self.logger.warning(f"Error detecting patterns: {e}")
            return {
                "has_codes": False,
                "code_count": 0,
                "error": str(e),
                "description": "Pattern detection unavailable"
            }

    def classify_content_type(self, image: Image.Image, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Classify the overall content type of the image based on various analyses.
        
        Args:
            image: PIL Image object
            analysis_data: Dictionary containing results from other analysis methods
            
        Returns:
            Dictionary with content classification
        """
       
        has_faces = analysis_data.get('face_detection', {}).get('has_faces', False)
        face_count = analysis_data.get('face_detection', {}).get('face_count', 0)
        has_text = analysis_data.get('text_extraction', {}).get('has_text', False)
        word_count = analysis_data.get('text_extraction', {}).get('word_count', 0)
        has_codes = analysis_data.get('pattern_detection', {}).get('has_codes', False)
        edge_complexity = analysis_data.get('edge_detection', {}).get('complexity', 'moderate')
        shape_count = analysis_data.get('shape_detection', {}).get('total_shapes', 0)
        
       
        content_types = []
        primary_type = "general image"
        
        if has_codes:
            content_types.append("barcode/QR code")
            primary_type = "barcode/QR code image"
        
        if has_faces:
            if face_count == 1:
                content_types.append("portrait")
                primary_type = "portrait/person photo"
            else:
                content_types.append("group photo")
                primary_type = "group photo"
        
        if has_text and word_count > 50:
            content_types.append("document")
            if not has_faces:
                primary_type = "document/text image"
        elif has_text and word_count > 5:
            content_types.append("text overlay")
        
        if shape_count > 10 and edge_complexity == "complex":
            content_types.append("diagram/illustration")
            if not has_faces and not has_text:
                primary_type = "diagram/illustration"
        

        img_array = np.array(image.convert('RGB'))
        avg_color = np.mean(img_array, axis=(0, 1))
        color_std = np.std(img_array, axis=(0, 1))
        
        if np.mean(color_std) < 20:
            content_types.append("low color variation")
            if not content_types or primary_type == "general image":
                primary_type = "simple/minimalist image"
        
        # Check if it's a screenshot (high resolution, text, shapes)
        width, height = image.size
        if has_text and shape_count > 5 and (width > 1000 or height > 1000):
            content_types.append("possible screenshot")
            primary_type = "screenshot/UI capture"
        
        
        description_parts = [f"This is a {primary_type}"]
        
        if has_faces:
            description_parts.append(f"featuring {face_count} person(s)")
        
        if has_text and word_count > 0:
            description_parts.append(f"with {word_count} words of text")
        
        if shape_count > 0:
            description_parts.append(f"containing {shape_count} geometric shapes")
        
        if has_codes:
            description_parts.append("including scannable codes")
        
        description = ". ".join(description_parts) + "."
        
        return {
            "primary_type": primary_type,
            "content_types": content_types,
            "description": description,
            "confidence": "high" if len(content_types) > 0 else "low"
        }

    def get_key_features(self, analysis_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and summarize key features of the image.
        
        Args:
            analysis_data: Dictionary containing all analysis results
            
        Returns:
            Dictionary with key features summary
        """
        features = []
        
        # Resolution and size
        resolution = analysis_data.get('resolution', {})
        width = resolution.get('width', 0)
        height = resolution.get('height', 0)
        features.append(f"Resolution: {width}x{height} pixels")
        
        # Aspect ratio
        aspect_ratio = analysis_data.get('aspect_ratio', {})
        ratio_str = aspect_ratio.get('ratio_string', 'unknown')
        features.append(f"Aspect ratio: {ratio_str}")
        
        # Color information
        dominant = analysis_data.get('dominant_color', {}).get('most_dominant', {})
        if dominant:
            hex_color = dominant.get('hex', '#000000')
            features.append(f"Dominant color: {hex_color}")
        
        # Brightness
        brightness = analysis_data.get('brightness', {})
        brightness_pct = brightness.get('brightness_percentage', 0)
        if brightness_pct < 30:
            features.append("Dark image")
        elif brightness_pct > 70:
            features.append("Bright image")
        else:
            features.append("Medium brightness")
        
        # Content features
        face_detection = analysis_data.get('face_detection', {})
        if face_detection.get('has_faces'):
            features.append(f"{face_detection.get('face_count')} face(s) detected")
        
        text_extraction = analysis_data.get('text_extraction', {})
        if text_extraction.get('has_text'):
            features.append(f"{text_extraction.get('word_count')} words of text")
        
        edge_detection = analysis_data.get('edge_detection', {})
        features.append(f"Edge complexity: {edge_detection.get('complexity', 'unknown')}")
        
        texture = analysis_data.get('texture_analysis', {})
        features.append(f"Texture: {texture.get('texture_type', 'unknown')}")
        
        pattern_detection = analysis_data.get('pattern_detection', {})
        if pattern_detection.get('has_codes'):
            features.append(f"{pattern_detection.get('code_count')} barcode/QR code(s)")
        
        return {
            "key_features": features,
            "summary": "; ".join(features)
        }

    def analyze_image(self, file_path: str) -> Dict[str, Any]:
        """
        Perform comprehensive analysis of an image file.
        
        Args:
            file_path: Path to the image file
            
        Returns:
            Dictionary containing all metrics
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image file not found: {file_path}")
        
        if not self.is_supported_format(file_path):
            raise ValueError(f"Unsupported file format: {Path(file_path).suffix}")
        
        try:
            
            with Image.open(file_path) as image:
                # Basic metrics
                resolution = self.get_resolution(image)
                aspect_ratio = self.get_aspect_ratio(resolution["width"], resolution["height"])
                file_format = self.get_file_format(image, file_path)
                file_stats = self.get_file_stats(file_path)
                brightness = self.get_average_brightness(image)
                avg_color = self.get_average_color(image)
                dominant_color = self.get_dominant_color(image)
                exif = self.get_exif_metadata(image)
                edit_frequency = self.calculate_edit_frequency(file_path)
                
                # Advanced content analysis
                self.logger.info("Performing edge detection...")
                edge_detection = self.detect_edges(image)
                
                self.logger.info("Detecting shapes...")
                shape_detection = self.detect_shapes(image)
                
                self.logger.info("Extracting text...")
                text_extraction = self.extract_text(image)
                
                self.logger.info("Detecting faces...")
                face_detection = self.detect_faces(image)
                
                self.logger.info("Analyzing texture...")
                texture_analysis = self.analyze_texture(image)
                
                self.logger.info("Detecting patterns...")
                pattern_detection = self.detect_patterns(image)
                
                # Build analysis data for classification
                analysis_data = {
                    "resolution": resolution,
                    "aspect_ratio": aspect_ratio,
                    "brightness": brightness,
                    "edge_detection": edge_detection,
                    "shape_detection": shape_detection,
                    "text_extraction": text_extraction,
                    "face_detection": face_detection,
                    "texture_analysis": texture_analysis,
                    "pattern_detection": pattern_detection,
                    "dominant_color": dominant_color
                }
                
                # Classify content type
                self.logger.info("Classifying content type...")
                content_classification = self.classify_content_type(image, analysis_data)
                
                # Extract key features
                key_features = self.get_key_features(analysis_data)
                
                return {
                    "file_path": str(Path(file_path).resolve()),
                    "file_name": Path(file_path).name,
                    
                    # Basic metrics
                    "resolution": resolution,
                    "aspect_ratio": aspect_ratio,
                    "format": file_format,
                    "file_stats": file_stats,
                    "brightness": brightness,
                    "average_color": avg_color,
                    "dominant_color": dominant_color,
                    "exif_metadata": exif,
                    "edit_frequency": edit_frequency,
                    
                    # Advanced content analysis
                    "edge_detection": edge_detection,
                    "shape_detection": shape_detection,
                    "text_extraction": text_extraction,
                    "face_detection": face_detection,
                    "texture_analysis": texture_analysis,
                    "pattern_detection": pattern_detection,
                    
                    # High-level classification
                    "content_classification": content_classification,
                    "key_features": key_features,
                    
                    "analysis_timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"Error analyzing image {file_path}: {e}")
            raise

    def batch_analyze(self, file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Analyze multiple images at once.
        
        Args:
            file_paths: List of paths to image files
            
        Returns:
            List of analysis results
        """
        results = []
        
        for file_path in file_paths:
            try:
                result = self.analyze_image(file_path)
                results.append(result)
            except Exception as e:
                self.logger.error(f"Failed to analyze {file_path}: {e}")
                results.append({
                    "file_path": file_path,
                    "error": str(e),
                    "analysis_timestamp": datetime.now().isoformat()
                })
        
        return results
