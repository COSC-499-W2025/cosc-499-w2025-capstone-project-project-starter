import json
from pathlib import Path
from typing import Union, Any


def to_json(data: Any, out_path: Union[str, Path]) -> None:
    """Write data to JSON file."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def from_json(file_path: Union[str, Path]) -> Any:
    """Read data from JSON file."""
    file_path = Path(file_path)
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)