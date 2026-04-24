import os
import time
import argparse
from pathlib import Path

def cleanup_old_files(directory, days=7):
    """Deletes files in the specified directory that are older than 'days'."""
    now = time.time()
    seconds = days * 24 * 60 * 60
    
    path = Path(directory)
    if not path.exists():
        print(f"📁 Directory {directory} does not exist, skipping cleanup.")
        return

    count = 0
    print(f"🧹 Cleaning up files in {directory} older than {days} days...")
    
    for item in path.iterdir():
        if item.is_file():
            if item.stat().st_mtime < now - seconds:
                try:
                    item.unlink()
                    count += 1
                except Exception as e:
                    print(f"⚠️ Could not delete {item.name}: {e}")
                    
    print(f"✨ Cleanup finished. Removed {count} files.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cleanup old temporary files.")
    parser.add_argument("--dir", type=str, required=True, help="Directory to clean")
    parser.add_argument("--days", type=int, default=7, help="Age of files to delete in days")
    
    args = parser.parse_args()
    cleanup_old_files(args.dir, args.days)
