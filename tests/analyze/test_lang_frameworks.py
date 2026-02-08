"""
Unit tests for Language and Framework Detection module
"""

import pytest
import tempfile
from pathlib import Path
from src.analyze.lang_frameworks import (
    detect_language_by_ext_and_shebang,
    detect_frameworks_from_source,
    detect_frameworks_from_manifests,
    merge_file_and_project_frameworks,
    get_supported_languages,
    get_supported_extensions
)

# Check if optional dependencies are available
try:
    import pygments
    HAS_PYGMENTS = True
except ImportError:
    HAS_PYGMENTS = False

try:
    import tomllib
    HAS_TOMLLIB = True
except ImportError:
    try:
        import toml
        HAS_TOMLLIB = True
    except ImportError:
        HAS_TOMLLIB = False

try:
    from requirements_parser import RequirementsFile
    HAS_REQ_PARSER = True
except ImportError:
    HAS_REQ_PARSER = False


class TestDetectLanguageByExtAndShebang:
    """Test suite for language detection by extension and shebang"""
    
    def test_python_by_extension(self):
        # Python file detected by .py extension
        language = detect_language_by_ext_and_shebang("app.py", "print('hello')")
        assert language == "python"
    
    def test_javascript_by_extension(self):
        # JavaScript file detected by .js extension
        language = detect_language_by_ext_and_shebang("app.js", "console.log('hello')")
        assert language == "javascript"
    
    def test_jsx_by_extension(self):
        # JSX file detected by .jsx extension
        language = detect_language_by_ext_and_shebang("Component.jsx", "const App = () => <div></div>")
        assert language == "javascript"
    
    def test_typescript_by_extension(self):
        # TypeScript file detected by .ts extension
        language = detect_language_by_ext_and_shebang("app.ts", "const x: number = 5")
        assert language == "typescript"
    
    def test_tsx_by_extension(self):
        # TSX file detected by .tsx extension
        language = detect_language_by_ext_and_shebang("Component.tsx", "const App = () => <div></div>")
        assert language == "typescript"
    
    def test_java_by_extension(self):
        # Java file detected by .java extension
        language = detect_language_by_ext_and_shebang("Main.java", "public class Main {}")
        assert language == "java"
    
    def test_cpp_by_extension(self):
        # C++ file detected by .cpp extension
        language = detect_language_by_ext_and_shebang("main.cpp", "#include <iostream>")
        assert language == "cpp"
    
    def test_c_by_extension(self):
        # C file detected by .c extension
        language = detect_language_by_ext_and_shebang("main.c", "#include <stdio.h>")
        assert language == "c"
    
    def test_header_by_extension(self):
        # Header file detected by .h extension
        language = detect_language_by_ext_and_shebang("header.h", "#ifndef HEADER_H")
        assert language == "c"
    
    def test_hpp_by_extension(self):
        # C++ header file detected by .hpp extension
        language = detect_language_by_ext_and_shebang("header.hpp", "#ifndef HEADER_HPP")
        assert language == "cpp"
    
    def test_csharp_by_extension(self):
        # C# file detected by .cs extension
        language = detect_language_by_ext_and_shebang("Program.cs", "using System;")
        assert language == "csharp"
    
    def test_go_by_extension(self):
        # Go file detected by .go extension
        language = detect_language_by_ext_and_shebang("main.go", "package main")
        assert language == "go"
    
    def test_ruby_by_extension(self):
        # Ruby file detected by .rb extension
        language = detect_language_by_ext_and_shebang("app.rb", "puts 'hello'")
        assert language == "ruby"
    
    def test_php_by_extension(self):
        # PHP file detected by .php extension
        language = detect_language_by_ext_and_shebang("index.php", "<?php echo 'hello'; ?>")
        assert language == "php"
    
    def test_kotlin_by_extension(self):
        # Kotlin file detected by .kt extension
        language = detect_language_by_ext_and_shebang("Main.kt", "fun main() {}")
        assert language == "kotlin"
    
    def test_swift_by_extension(self):
        # Swift file detected by .swift extension
        language = detect_language_by_ext_and_shebang("App.swift", "import UIKit")
        assert language == "swift"
    
    def test_python_shebang(self):
        # Python detected by shebang when no extension
        content = "#!/usr/bin/env python\nprint('hello')"
        language = detect_language_by_ext_and_shebang("script", content)
        assert language == "python"
    
    def test_python3_shebang(self):
        # Python detected by python3 shebang
        content = "#!/usr/bin/env python3\nprint('hello')"
        language = detect_language_by_ext_and_shebang("script", content)
        assert language == "python"
    
    def test_node_shebang(self):
        # JavaScript detected by node shebang
        content = "#!/usr/bin/env node\nconsole.log('hello')"
        language = detect_language_by_ext_and_shebang("script", content)
        assert language == "javascript"
    
    def test_ruby_shebang(self):
        # Ruby detected by ruby shebang
        content = "#!/usr/bin/env ruby\nputs 'hello'"
        language = detect_language_by_ext_and_shebang("script", content)
        assert language == "ruby"
    
    def test_bash_shebang(self):
        # Bash detected by bash shebang
        content = "#!/bin/bash\necho 'hello'"
        language = detect_language_by_ext_and_shebang("script", content)
        assert language == "shell"
    
    def test_sh_shebang(self):
        # Shell detected by sh shebang
        content = "#!/bin/sh\necho 'hello'"
        language = detect_language_by_ext_and_shebang("script", content)
        assert language == "shell"
    
    def test_extension_overrides_shebang(self):
        # Extension takes precedence over shebang
        content = "#!/bin/bash\nprint('hello')"
        language = detect_language_by_ext_and_shebang("app.py", content)
        assert language == "python"
    
    def test_unknown_extension_no_shebang(self):
        # Unknown file without shebang returns unknown (or text/plaintext if Pygments available)
        language = detect_language_by_ext_and_shebang("file.xyz", "some content")
        # Without Pygments: "unknown", with Pygments: might detect "text only" or similar
        assert language in ["unknown", "text only", "text", "plaintext"]
    
    def test_cc_extension(self):
        # .cc extension detected as cpp
        language = detect_language_by_ext_and_shebang("main.cc", "#include <iostream>")
        assert language == "cpp"


class TestDetectFrameworksFromSource:
    """Test suite for framework detection from source code"""
    
    def test_python_fastapi(self):
        # FastAPI detected in Python code
        code = "from fastapi import FastAPI\napp = FastAPI()"
        frameworks = detect_frameworks_from_source("python", code)
        assert "fastapi" in frameworks
    
    def test_python_django(self):
        # Django detected in Python code
        code = "from django.db import models"
        frameworks = detect_frameworks_from_source("python", code)
        assert "django" in frameworks
    
    def test_python_flask(self):
        # Flask detected in Python code
        code = "from flask import Flask\napp = Flask(__name__)"
        frameworks = detect_frameworks_from_source("python", code)
        assert "flask" in frameworks
    
    def test_python_sqlalchemy(self):
        # SQLAlchemy detected in Python code
        code = "from sqlalchemy import Column"
        frameworks = detect_frameworks_from_source("python", code)
        assert "sqlalchemy" in frameworks
    
    def test_python_pytest(self):
        # Pytest detected in Python code
        code = "import pytest\ndef test_something(): pass"
        frameworks = detect_frameworks_from_source("python", code)
        assert "pytest" in frameworks
    
    def test_python_pandas(self):
        # Pandas detected in Python code
        code = "import pandas as pd"
        frameworks = detect_frameworks_from_source("python", code)
        assert "pandas" in frameworks
    
    def test_python_numpy(self):
        # NumPy detected in Python code
        code = "import numpy as np"
        frameworks = detect_frameworks_from_source("python", code)
        assert "numpy" in frameworks
    
    def test_javascript_react(self):
        # React detected in JavaScript code
        code = "import React from 'react'"
        frameworks = detect_frameworks_from_source("javascript", code)
        assert "react" in frameworks
    
    def test_javascript_vue(self):
        # Vue detected in JavaScript code
        code = "import Vue from 'vue'"
        frameworks = detect_frameworks_from_source("javascript", code)
        assert "vue" in frameworks
    
    def test_javascript_angular(self):
        # Angular detected in JavaScript code
        code = "import { Component } from '@angular/core'"
        frameworks = detect_frameworks_from_source("javascript", code)
        assert "angular" in frameworks
    
    def test_javascript_express(self):
        # Express detected in JavaScript code
        code = "const express = require('express')"
        frameworks = detect_frameworks_from_source("javascript", code)
        assert "express" in frameworks
    
    def test_javascript_jest(self):
        # Jest detected in JavaScript code
        code = "describe('test', () => {})"
        frameworks = detect_frameworks_from_source("javascript", code)
        assert "jest" in frameworks
    
    def test_typescript_react(self):
        # React detected in TypeScript code
        code = "import React from 'react'"
        frameworks = detect_frameworks_from_source("typescript", code)
        assert "react" in frameworks
    
    def test_java_spring(self):
        # Spring detected in Java code
        code = "import org.springframework.boot.SpringApplication"
        frameworks = detect_frameworks_from_source("java", code)
        assert "spring" in frameworks
    
    def test_java_hibernate(self):
        # Hibernate detected in Java code
        code = "import org.hibernate.Session"
        frameworks = detect_frameworks_from_source("java", code)
        assert "hibernate" in frameworks
    
    def test_java_junit(self):
        # JUnit detected in Java code
        code = "import org.junit.Test"
        frameworks = detect_frameworks_from_source("java", code)
        assert "junit" in frameworks
    
    def test_cpp_boost(self):
        # Boost detected in C++ code
        code = "#include <boost/algorithm/string.hpp>"
        frameworks = detect_frameworks_from_source("cpp", code)
        assert "boost" in frameworks
    
    def test_cpp_qt(self):
        # Qt detected in C++ code
        code = "#include <QApplication>"
        frameworks = detect_frameworks_from_source("cpp", code)
        assert "qt" in frameworks
    
    def test_cpp_opencv(self):
        # OpenCV detected in C++ code
        code = "#include <opencv2/core.hpp>"
        frameworks = detect_frameworks_from_source("cpp", code)
        assert "opencv" in frameworks
    
    def test_multiple_frameworks(self):
        # Multiple frameworks detected
        code = "from fastapi import FastAPI\nfrom sqlalchemy import Column"
        frameworks = detect_frameworks_from_source("python", code)
        assert "fastapi" in frameworks
        assert "sqlalchemy" in frameworks
    
    def test_unknown_language_returns_empty(self):
        # Unknown language returns empty list
        frameworks = detect_frameworks_from_source("unknown", "some code")
        assert frameworks == []
    
    def test_no_frameworks_detected(self):
        # Code without frameworks returns empty list
        code = "def hello():\n    print('hello')"
        frameworks = detect_frameworks_from_source("python", code)
        assert frameworks == []


class TestDetectFrameworksFromManifests:
    """Test suite for framework detection from manifest files"""
    
    def test_package_json_detection(self):
        # Multiple frameworks detected from package.json
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            package_json = project_root / "package.json"
            package_json.write_text('{"dependencies": {"react": "^18.0.0", "express": "^4.0.0"}, "devDependencies": {"vue": "^3.0.0"}}')
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "react" in frameworks
            assert "express" in frameworks
            assert "vue" in frameworks
    
    def test_requirements_txt_detection(self):
        # Python frameworks detected from requirements.txt
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            requirements = project_root / "requirements.txt"
            requirements.write_text("django==4.2.0\nfastapi==0.95.0\nflask==2.3.0")
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "django" in frameworks
            assert "fastapi" in frameworks
            assert "flask" in frameworks
    
    def test_pyproject_toml_with_django(self):
        # Django detected from pyproject.toml
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            pyproject = project_root / "pyproject.toml"
            pyproject.write_text('[tool.poetry.dependencies]\ndjango = "^4.2.0"')
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "django" in frameworks
    
    def test_pom_xml_detection(self):
        # Java frameworks detected from pom.xml
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            pom = project_root / "pom.xml"
            pom.write_text('''<project>
                <dependencies>
                    <dependency><groupId>org.springframework.boot</groupId></dependency>
                    <dependency><artifactId>hibernate-core</artifactId></dependency>
                </dependencies>
            </project>''')
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "spring" in frameworks
            assert "hibernate" in frameworks
    
    def test_gradle_detection(self):
        # Spring detected from build.gradle
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            gradle = project_root / "build.gradle"
            gradle.write_text("dependencies { implementation 'org.springframework.boot:spring-boot-starter' }")
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "spring" in frameworks
    
    def test_cmake_detection(self):
        # C++ frameworks detected from CMakeLists.txt
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            cmake = project_root / "CMakeLists.txt"
            cmake.write_text('find_package(Qt5 REQUIRED)\nfind_package(Boost REQUIRED)\nfind_package(OpenCV REQUIRED)')
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "qt" in frameworks
            assert "boost" in frameworks
            assert "opencv" in frameworks
    
    def test_no_manifest_files_returns_empty(self):
        # No manifest files returns empty set
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            frameworks = detect_frameworks_from_manifests(project_root)
            assert frameworks == set()
    
    def test_invalid_json_handled_gracefully(self):
        # Invalid JSON handled without crashing
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            package_json = project_root / "package.json"
            package_json.write_text('{ invalid json')
            
            frameworks = detect_frameworks_from_manifests(project_root)
            # Should return empty or partial results, not crash
            assert isinstance(frameworks, set)
    
    def test_multiple_manifest_files(self):
        # Frameworks detected from multiple manifest files
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            
            package_json = project_root / "package.json"
            package_json.write_text('{"dependencies": {"react": "^18.0.0"}}')
            
            requirements = project_root / "requirements.txt"
            requirements.write_text("django==4.2.0")
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "react" in frameworks
            assert "django" in frameworks


class TestMergeFileAndProjectFrameworks:
    """Test suite for merging file and project-level frameworks"""
    
    def test_merge_disjoint_frameworks(self):
        # Merge frameworks with no overlap
        file_fw = ["fastapi", "sqlalchemy"]
        project_fw = {"django", "pytest"}
        
        merged = merge_file_and_project_frameworks(file_fw, project_fw)
        
        assert "fastapi" in merged
        assert "sqlalchemy" in merged
        assert "django" in merged
        assert "pytest" in merged
    
    def test_merge_with_duplicates(self):
        # Duplicates removed when merging
        file_fw = ["react", "jest"]
        project_fw = {"react", "webpack"}
        
        merged = merge_file_and_project_frameworks(file_fw, project_fw)
        
        assert merged.count("react") == 1
        assert "jest" in merged
        assert "webpack" in merged
    
    def test_merge_empty_file_frameworks(self):
        # Empty file frameworks with project frameworks
        file_fw = []
        project_fw = {"django", "pytest"}
        
        merged = merge_file_and_project_frameworks(file_fw, project_fw)
        
        assert "django" in merged
        assert "pytest" in merged
    
    def test_merge_empty_project_frameworks(self):
        # File frameworks with empty project frameworks
        file_fw = ["fastapi", "sqlalchemy"]
        project_fw = set()
        
        merged = merge_file_and_project_frameworks(file_fw, project_fw)
        
        assert "fastapi" in merged
        assert "sqlalchemy" in merged
    
    def test_merge_both_empty(self):
        # Both empty returns empty list
        file_fw = []
        project_fw = set()
        
        merged = merge_file_and_project_frameworks(file_fw, project_fw)
        
        assert merged == []
    
    def test_merge_preserves_order(self):
        # File frameworks appear first, then project frameworks
        file_fw = ["fastapi", "sqlalchemy"]
        project_fw = {"django"}
        
        merged = merge_file_and_project_frameworks(file_fw, project_fw)
        
        # File frameworks should be at the start
        assert merged[:2] == ["fastapi", "sqlalchemy"]


class TestUtilityFunctions:
    """Test suite for utility functions"""
    
    def test_get_supported_languages(self):
        # Returns list of supported languages
        languages = get_supported_languages()
        assert isinstance(languages, list)
        assert "python" in languages
        assert "javascript" in languages
        assert "java" in languages
        assert len(languages) > 0
    
    def test_get_supported_extensions(self):
        # Returns list of supported extensions
        extensions = get_supported_extensions()
        assert isinstance(extensions, list)
        assert ".py" in extensions
        assert ".js" in extensions
        assert ".java" in extensions
        assert len(extensions) > 0


class TestImprovedParsing:
    """Test suite for improved parsing with optional libraries"""
    
    @pytest.mark.skipif(not HAS_PYGMENTS, reason="pygments not installed")
    def test_language_fallback_pygments(self):
        # Python code without extension - Pygments should detect it
        python_content = """import sys

def main():
    print("Hello, World!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
"""
        language = detect_language_by_ext_and_shebang("unknown_file", python_content)
        # Pygments should detect Python (most reliable detection)
        assert language != "unknown", f"Expected language detection via Pygments, got: {language}"
        assert "python" in language.lower() or language == "python3"
    
    def test_language_fallback_python_known_extension(self):
        # Python with known extension should use extension, not Pygments
        python_content = "def hello():\n    print('world')"
        language = detect_language_by_ext_and_shebang("test.py", python_content)
        assert language == "python"
    
    @pytest.mark.skipif(not HAS_TOMLLIB, reason="tomllib/toml not available")
    def test_pyproject_parsing_tomllib(self):
        # Parse pyproject.toml with tomllib for robust detection
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            pyproject = project_root / "pyproject.toml"
            pyproject.write_text("""[project]
name = "test-project"
version = "0.0.1"
dependencies = [
    "fastapi>=0.110.0",
    "sqlalchemy>=2.0",
    "pytest>=7.0"
]
""")
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "fastapi" in frameworks
            assert "sqlalchemy" in frameworks
            assert "pytest" in frameworks
    
    @pytest.mark.skipif(not HAS_TOMLLIB, reason="tomllib/toml not available")
    def test_pyproject_poetry_parsing(self):
        # Parse poetry-style pyproject.toml
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            pyproject = project_root / "pyproject.toml"
            pyproject.write_text("""[tool.poetry]
name = "poetry-project"
version = "1.0.0"

[tool.poetry.dependencies]
python = "^3.11"
django = "^4.2"
pandas = "^2.0"
""")
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "django" in frameworks
            assert "pandas" in frameworks
    
    def test_requirements_fallback_without_parser(self):
        # Without requirements-parser, should still detect via substring
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            requirements = project_root / "requirements.txt"
            requirements.write_text("django==4.2.1\nflask>=2.3.0")
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "django" in frameworks
            assert "flask" in frameworks
    
    def test_package_json_parse(self):
        # Parse package.json with dependencies and devDependencies
        with tempfile.TemporaryDirectory() as temp_dir:
            project_root = Path(temp_dir)
            package_json = project_root / "package.json"
            package_json.write_text("""{
    "name": "test-app",
    "version": "1.0.0",
    "dependencies": {
        "react": "^18.2.0",
        "express": "^4.18.0"
    },
    "devDependencies": {
        "jest": "^29.5.0",
        "webpack": "^5.0.0"
    }
}""")
            
            frameworks = detect_frameworks_from_manifests(project_root)
            assert "react" in frameworks
            assert "jest" in frameworks
            assert "express" in frameworks
            assert "webpack" in frameworks
    
    def test_merge_file_and_project_frameworks_dedupe(self):
        # Ensure deduplication when merging frameworks
        file_fw = ["flask", "pytest"]
        project_fw = {"pytest", "sqlalchemy", "django"}
        
        result = merge_file_and_project_frameworks(file_fw, project_fw)
        
        # File frameworks come first
        assert result[0] == "flask"
        assert result[1] == "pytest"
        # Project frameworks added after (sorted)
        assert "sqlalchemy" in result
        assert "django" in result
        # No duplicates
        assert result.count("pytest") == 1
        assert len(result) == 4

