from pathlib import Path
from typing import Dict, Literal

TextLabel = Literal["binary", "text"]

# Byte ranges we consider "texty" when judging raw bytes
# Allow tabs/newlines/carriage returns and common ASCII 
_PRINTABLE_ASCII = set(range(32, 127)) | {9, 10, 13}

def _looks_like_utf16(chunk: bytes) -> str | None:
    """Return 'utf-16-le' or 'utf-16-be' if the chunk plausibly looks like UTF-16 without BOM."""
    if len(chunk) < 2:
        return None
    # many NULs in even or odd positions suggests UTF-16.
    even_nuls = sum(1 for i in range(0, len(chunk), 2) if chunk[i] == 0)
    odd_nuls  = sum(1 for i in range(1, len(chunk), 2) if chunk[i] == 0)
    total_pairs = len(chunk) // 2 or 1
    # if around 30% of positions in one parity are null byte (0x00), consider it utf16. 
    if even_nuls / total_pairs >= 0.3 and odd_nuls / total_pairs < 0.1:
        return "utf-16-be"  # high chance bytes at even positions are nul => be
    if odd_nuls / total_pairs >= 0.3 and even_nuls / total_pairs < 0.1:
        return "utf-16-le"  # high chance bytes at odd positions are nul => le
    return None

def _printable_ratio(chunk: bytes) -> float:
    """Share of bytes that look like text-ish ASCII/UTF-8 lead/trail bytes is tricky;
    keep it simple: count ASCII printables + whitespace."""
    printable = sum(1 for b in chunk if (b in _PRINTABLE_ASCII))
    return printable / max(1, len(chunk))

def _read_samples(fp, sample_size: int) -> list[bytes]:
    """Read head and, if large enough, a later sample to reduce false negatives"""
    head = fp.read(sample_size)
    if not head:
        return [b""]
    # If file is small, just return head.
    try:
        size = fp.seek(0, 2)  # end
        if size <= sample_size * 2:
            fp.seek(0)
            return [head]
        # Take a later sample roughly mid-file if it's big
        mid_pos = max(sample_size, size // 2)
        fp.seek(mid_pos)
        mid = fp.read(sample_size)
        fp.seek(0)
        return [head, mid]
    except OSError:
        return [head]

def is_binary_file(file_path: Path, sample_size: int = 4096) -> bool:
    """
    Guess if a given file is human readable.
      - handle BOM (byte order mark, see https://en.wikipedia.org/wiki/Byte_order_mark) for UTF-8/16/32
      - Allow UTF-16/32 even with NULs
      - If decoding fails, fall back to printable ratio
      - Sample head and mid to lower false negatives
    """
    try:
        with open(file_path, "rb") as f:
            samples = _read_samples(f, sample_size)
    except (OSError, PermissionError):
        return True

    # Empty file is text.
    if not samples or not samples[0]:
        return False

    for chunk in samples:
        # BOM checks
        if chunk.startswith(b"\xef\xbb\xbf"):
            return False  # UTF-8 BOM
        if chunk.startswith(b"\xff\xfe\x00\x00") or chunk.startswith(b"\x00\x00\xfe\xff"):
            return False  # UTF-32 with BOM
        if chunk.startswith(b"\xff\xfe") or chunk.startswith(b"\xfe\xff"):
            return False  # UTF-16 with BOM

        # is it pure UTF-8?
        try:
            chunk.decode("utf-8")
            # It probably is. Carry on
            continue
        except UnicodeDecodeError:
            pass

        # Maybe not utf8. Utf-16?
        enc = _looks_like_utf16(chunk)
        if enc:
            try:
                chunk.decode(enc)
                continue
            except UnicodeDecodeError:
                pass

        # If we're here, it's reasonable to assume it's binary.
        if b"\x00" in chunk:
            return True

        # "texty" ratio 
        if _printable_ratio(chunk) < 0.70:
            return True
    return False


def classify_files_under(root_path: str) -> Dict[Path, TextLabel]:
    """
    Recursively walk root_path and classify files as binary or text.
    """
    root = Path(root_path)
    results: Dict[Path, TextLabel] = {}

    paths = [root] if root.is_file() else root.rglob("*")
    for p in paths:
        if not p.is_file():
            continue
        results[p] = "binary" if is_binary_file(p) else "text"

    return results
