import os
import shutil
import stat
import logging
from pathlib import Path
import time


logging.basicConfig(filename=f'logs/sync-{int(time.time())}.log', 
                   level=logging.INFO, format='%(asctime)s %(message)s')


class Sync:
    def __init__(self, source: str, backup: str):
        self.source = Path(source)
        self.backup = Path(backup)


    def clear_deleted(self, dry=True):
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
                shutil.rmtree(root) if not dry else None
            else:
                for file in files:
                    src_equiv = self.source / rel_path / file
                    if not src_equiv.exists():
                        logging.info(f"Deleting file: {root / file}")
                        os.remove(root / file) if not dry else None
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