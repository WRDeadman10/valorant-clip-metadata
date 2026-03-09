import os
import re
from datetime import datetime, timezone, timedelta

# IST is UTC+5:30
IST_OFFSET = timedelta(hours=5, minutes=30)
IST_TZ = timezone(IST_OFFSET)

def get_clip_timestamp(file_path: str) -> datetime:
    """
    Extracts the creation timestamp of a video clip from its Tracker Network filename 
    or its parent folder name assuming the timestamp is in IST.
    Falls back to OS metadata if extraction fails.
    Returns a timezone-aware UTC datetime object.
    """
    filename = os.path.basename(file_path)
    parent_dir = os.path.basename(os.path.dirname(file_path))
    
    # Common TRN format: VALORANT 03-01-2026 21-55-27-905.mp4
    # or VALORANT_03-01-2026_21-54-28-579
    # Hours can be single digit! Example: VALORANT 03-04-2026 0-54-52-228.mp4
    pattern = r'(\d{1,2})-(\d{1,2})-(\d{4})[ _](\d{1,2})-(\d{1,2})-(\d{1,2})'
    
    match = re.search(pattern, filename) or re.search(pattern, parent_dir)
    
    if match:
        p1, p2, year, hour, minute, second = map(int, match.groups())
        
        # In TRN recorded files it's usually MM-DD-YYYY. Safeguard if p1 > 12.
        if p1 > 12:
            month, day = p2, p1
        else:
            month, day = p1, p2
            
        try:
            # Construct timezone-aware datetime representing IST
            dt_ist = datetime(year, month, day, hour, minute, second, tzinfo=IST_TZ)
            # Return converted UTC datetime
            return dt_ist.astimezone(timezone.utc)
        except ValueError as e:
            print(f"Warning: Failed to parse extracted timestamp {match.group(0)}: {e}")
            pass
            
    # Fallback to OS stat if string parsing fails
    stat = os.stat(file_path)
    timestamp = min(stat.st_mtime, stat.st_ctime)
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

