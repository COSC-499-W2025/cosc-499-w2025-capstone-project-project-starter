"""Zip file ingestion package."""

from .zip_parser import parse_zip, ZipParseError
from .models import ZipIndex, ZipEntry

__all__ = ['parse_zip', 'ZipParseError', 'ZipIndex', 'ZipEntry']