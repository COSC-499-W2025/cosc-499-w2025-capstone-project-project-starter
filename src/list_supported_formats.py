"""
Display all supported file formats with descriptions.
"""
from parsers.document_parser import DocumentParser


def main():
    """Display all supported file formats."""
    print("\n" + "="*70)
    print("📚 Document Summarization - Supported File Formats")
    print("="*70 + "\n")
    
    formats = {
        "📄 Documents": [
            (".docx", "Microsoft Word documents"),
            (".pdf", "PDF documents"),
            (".rtf", "Rich Text Format documents"),
            (".txt", "Plain text files"),
            (".md", "Markdown files"),
            (".rst", "reStructuredText files")
        ],
        "🎯 Presentations": [
            (".pptx", "Microsoft PowerPoint presentations")
        ],
        "📊 Spreadsheets": [
            (".csv", "Comma-separated values"),
            (".xlsx", "Microsoft Excel spreadsheets"),
            (".xls", "Legacy Excel spreadsheets")
        ],
        "💻 Code Files": [
            (".py", "Python"),
            (".js", "JavaScript"),
            (".ts", "TypeScript"),
            (".jsx", "React JavaScript"),
            (".tsx", "React TypeScript"),
            (".java", "Java"),
            (".cpp", "C++"),
            (".c", "C"),
            (".h", "C/C++ headers"),
            (".hpp", "C++ headers"),
            (".go", "Go"),
            (".rs", "Rust"),
            (".rb", "Ruby"),
            (".php", "PHP"),
            (".swift", "Swift"),
            (".kt", "Kotlin"),
            (".cs", "C#"),
            (".r", "R"),
            (".m", "Objective-C/MATLAB")
        ],
        "🌐 Markup & Data": [
            (".html", "HTML documents"),
            (".htm", "HTML documents"),
            (".xml", "XML documents"),
            (".json", "JSON data"),
            (".yaml", "YAML configuration"),
            (".yml", "YAML configuration")
        ]
    }
    
    total_count = 0
    
    for category, file_types in formats.items():
        print(f"{category}")
        print("-" * 70)
        for ext, description in file_types:
            print(f"  {ext:10} → {description}")
            total_count += 1
        print()
    
    print("=" * 70)
    print(f"✨ Total Supported Formats: {total_count}")
    print("=" * 70)
    
    # Test with DocumentParser
    print("\n📋 Verification with DocumentParser:")
    supported = DocumentParser.get_supported_formats()
    print(f"   Parser reports {len(supported)} supported formats")
    print(f"   Formats: {', '.join(sorted(supported))}")
    
    print("\n💡 Usage:")
    print("   python test_summarization.py <file_path>")
    print("\n")


if __name__ == "__main__":
    main()



