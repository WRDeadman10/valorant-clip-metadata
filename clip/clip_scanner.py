import os
from pathlib import Path
from typing import List
from datetime import datetime

from config import config
from clip.timestamp_parser import get_clip_timestamp

class ClipInfo:
    """
    Represents metadata about a specific video clip file on disk.
    """
    def __init__(self, file_path: str, timestamp: datetime):
        self.file_path = file_path
        self.filename = os.path.basename(file_path)
        self.timestamp = timestamp
        
    def __repr__(self):
        return f"<ClipInfo {self.filename} @ {self.timestamp.isoformat()}>"

def scan_clips_directory(directory_path: str) -> List[ClipInfo]:
    """
    Scans a directory for supported video files and extracts their creation timestamps.
    Returns a list of ClipInfo objects sorted by timestamp (oldest first).
    """
    clips = []
    path = Path(directory_path)
    
    if not path.exists() or not path.is_dir():
        raise FileNotFoundError(f"Directory not found: {directory_path}")
        
    for file_path in path.iterdir():
        if file_path.is_file() and file_path.suffix.lower() in config.SUPPORTED_VIDEO_FORMATS:
            try:
                # Extract creation or modification time to map back to a match
                timestamp = get_clip_timestamp(str(file_path))
                clips.append(ClipInfo(str(file_path), timestamp))
            except Exception as e:
                print(f"Warning: Could not process {file_path.name}: {e}")
                
    # Sort clips chronologically so we process them in the natural sequence
    clips.sort(key=lambda x: x.timestamp)
    return clips
