"""Module entry point: python -m src.pipeline <subcommand> [args...]"""
import sys
from src.pipeline.cli import main

if __name__ == "__main__":
    sys.exit(main())
