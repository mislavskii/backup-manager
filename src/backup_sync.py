import os
import shutil
import stat
import logging
from pathlib import Path
import time
from tqdm import tqdm

from utils import remove_directory, remove_file, progress_tracker, make_directory, copy_file


logging.basicConfig(filename=f'logs/sync-{int(time.time())}.log', 
                   level=logging.INFO, format='%(asctime)s %(message)s')


class Sync:
    def __init__(self, source: str, backup: str):
        self.source = Path(source)
        self.backup = Path(backup)

    @progress_tracker(desc="Clearing deleted files", unit="dirs")
    def clear_deleted(self, dry=True, pbar=None):
        """
        Clearing the backup of items no longer found in the source
        """
        for root, dirs, files in self.backup.walk():
        # for root, dirs, files in tqdm(self.backup.walk()):
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
                make_directory(backup_equiv)
            for file in files:
                if not dry:
                    copy_file(root / file, backup_equiv / file)
            time.sleep(0.01)  # Yield to prevent I/O starvation


if __name__ == "__main__":
    source = '/media/mm/MSI M450/SSD_RESCUE/User'
    backup = '/media/mm/MSI M450/Backup/User'
    sync = Sync(source, backup)  
    sync.clear_deleted(dry=False)
