import os
import shutil
import stat
import logging
from pathlib import Path
import time
import functools


logging.basicConfig(filename=f'logs/sync-{int(time.time())}.log', 
                   level=logging.INFO, format='%(asctime)s %(message)s')


def retry_on_failure(max_retries=1, delay=0.1):
    """
    Decorator to retry a function on failure with logging
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = Exception("Unknown error")
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logging.warning(f"Failed to execute {func.__name__} on attempt {attempt + 1}: {e}")
                        time.sleep(delay)
                    else:
                        logging.error(f"Failed to execute {func.__name__} after {max_retries + 1} attempts: {e}")
                        # Instead of raising, we just return None to skip to next item
                        return None
        return wrapper
    return decorator


class Sync:
    def __init__(self, source: str, backup: str):
        self.source = Path(source)
        self.backup = Path(backup)

    @retry_on_failure()
    def _remove_directory(self, path):
        """Remove a directory with retry logic"""
        shutil.rmtree(path)

    @retry_on_failure()
    def _remove_file(self, path):
        """Remove a file with retry logic"""
        os.remove(path)

    def clear_deleted(self, dry=True):
        # TODO: error handling
        """
        Clearing the backup of items no longer found in the source
        """
        for root, dirs, files in self.backup.walk():
            if not root.exists():
                continue
            rel_path = root.relative_to(self.backup)
            src_equiv = self.source / rel_path
            if not src_equiv.exists():
                logging.info(f"Deleting dir tree: {root}")
                if not dry:
                    self._remove_directory(root)
            else:
                for file in files:
                    src_equiv = self.source / rel_path / file
                    if not src_equiv.exists():
                        logging.info(f"Deleting file: {root / file}")
                        if not dry:
                            self._remove_file(root / file)
            time.sleep(0.01)  # Yield to prevent I/O starvation


# All below will be refactored later
def safe_copy(src, dst):
    try:
        if src.is_file():
            logging.info(f"Copying: {src} -> {dst}")
            shutil.copy2(src, dst, follow_symlinks=False)
        elif src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed {src}: {e}")

def sync_level(depth=0, max_depth=0, dry_run=True):
    """Batch sync by directory depth to avoid NTFS recursion freeze"""
    count = 0
    for root, dirs, files in os.walk(source, topdown=True):
        root = Path(root)
        rel_path = root.relative_to(source)
        depth_now = len(rel_path.parts)
        
        if depth_now > max_depth and max_depth > 0:
            dirs[:] = []  # Prune deeper recursion
            continue
            
        dest_root = backup / rel_path
        for file in files:
            safe_copy(root / file, dest_root / file)
            count += 1
            
        if count % 100 == 0:
            print(f"Processed {count} files at depth {depth_now}")
            
        time.sleep(0.01)  # Yield to prevent I/O starvation
    


if __name__ == "__main__":
    # print("DRY RUN MODE - remove dry_run=True for real sync")
    sync_level(max_depth=2)  # Start shallow
    print("Check /tmp/sync-*.log then increase max_depth")