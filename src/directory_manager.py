#!/usr/bin/env python3
import sys
from pathlib import Path
from typing import List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


def ensure_directories() -> None:
    """Ensure all required directories exist."""
    required_dirs = [
        "data/raw_emails",
        "data/processed",
        "data/processed/temp",
        "data/attachments"
    ]

    for dir_path in required_dirs:
        create_directory(dir_path)


def create_directory(path: str) -> None:
    """Create a directory if it doesn't exist."""
    try:
        Path(path).mkdir(parents=True, exist_ok=True)
        print(f"Ensured directory exists: {path}")
    except Exception as e:
        print(f"Error creating directory {path}: {str(e)}")


def get_output_path(base_dir: str, filename: str, extension: str = "") -> Path:
    """
    Generate an output path for a file.
    Ensures the base directory exists and returns a Path object.
    """
    try:
        base_path = Path(base_dir)
        base_path.mkdir(parents=True, exist_ok=True)
        return base_path / f"{filename}{extension}"
    except Exception as e:
        print(f"Error generating output path: {str(e)}")
        raise


def validate_paths(paths: List[str]) -> List[str]:
    """
    Validate a list of paths.
    Returns list of valid paths, logs any invalid ones.
    """
    valid_paths = []
    for path in paths:
        if validate_path(path):
            valid_paths.append(path)
    return valid_paths


def validate_path(path: str) -> bool:
    """
    Validate a single path.
    Returns True if path is valid, False otherwise.
    """
    try:
        path_obj = Path(path)

        # Check if path is absolute and within project directory
        if path_obj.is_absolute():
            project_root = Path.cwd()
            if not str(path_obj).startswith(str(project_root)):
                print(f"Path {path} is outside project directory")
                return False

        # Check if parent directories exist
        if not path_obj.parent.exists():
            print(f"Parent directory does not exist for {path}")
            return False

        return True

    except Exception as e:
        print(f"Error validating path {path}: {str(e)}")
        return False


def cleanup_directory(directory: str, pattern: str = "*") -> None:
    """
    Clean up files in a directory matching the given pattern.
    """
    try:
        dir_path = Path(directory)
        if dir_path.exists():
            for item in dir_path.glob(pattern):
                if item.is_file():
                    item.unlink()
            print(f"Cleaned up directory: {directory}")
    except Exception as e:
        print(f"Error cleaning up directory {directory}: {str(e)}")


def get_file_paths(directory: str, pattern: str = "*") -> List[Path]:
    """
    Get all file paths in a directory matching the given pattern.
    """
    try:
        dir_path = Path(directory)
        if not dir_path.exists():
            print(f"Directory does not exist: {directory}")
            return []

        return list(dir_path.glob(pattern))

    except Exception as e:
        print(f"Error getting file paths from {directory}: {str(e)}")
        return []
