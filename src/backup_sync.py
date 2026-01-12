import os
import shutil
import stat
import logging
from pathlib import Path
import time
from tqdm import tqdm

from utils import remove_directory, remove_file, progress_tracker


logging.basicConfig(filename=f'logs/sync-{int(time.time())}.log', 
                   level=logging.INFO, format='%(asctime)s %(message)s')


class Sync:
    def __init__(self, source: str, backup: str):
        self.source = Path(source)
        self.backup = Path(backup)

    # @progress_tracker(desc="Clearing deleted files", unit="dirs")
    def clear_deleted(self, dry=True, pbar=None):
        """
        Clearing the backup of items no longer found in the source
        """
        # for root, dirs, files in self.backup.walk():
        for root, dirs, files in tqdm(self.backup.walk()):
            if not root.exists():
                if pbar:
                    pbar.update(1)
                continue
            rel_path = root.relative_to(self.backup)
            src_equiv = self.source / rel_path
            if not src_equiv.exists():
                logging.info(f"Deleting dir tree: {root}")
                if not dry:
                    remove_directory(root)
            else:
                for file in files:
                    src_equiv = self.source / rel_path / file
                    if not src_equiv.exists():
                        logging.info(f"Deleting file: {root / file}")
                        if not dry:
                            remove_file(root / file)
            if pbar:
                pbar.update(1)
            time.sleep(0.01)  # Yield to prevent I/O starvation


    def safe_copy(self, dry=True): # TODO: test, implement error handling and progress bar
        """Copies all files recursively from source to backup with no metadata"""
        for root, dirs, files in self.source.walk():
            rel_path = root.relative_to(self.source)
            backup_equiv = self.backup / rel_path
            logging.info(f"Making dir: {root}")
            if not dry:
                backup_equiv.mkdir(parents=True, exist_ok=True)
            for file in files:
                if not dry:
                    shutil.copy(root / file, backup_equiv / file)
            time.sleep(0.01)  # Yield to prevent I/O starvation

    


# All below will be refactored later


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
    source = '/media/mm/MSI M450/SSD_RESCUE/User'
    backup = '/media/mm/MSI M450/Backup/User'
    sync = Sync(source, backup)  
    sync.clear_deleted()
