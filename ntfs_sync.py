#!/usr/bin/env python3
import os
import shutil
import stat
import logging
from pathlib import Path
import time

source = Path("/media/mm/DEXP C100/User")
backup = Path("/media/mm/Backup/User")

logging.basicConfig(filename=f'/tmp/sync-{int(time.time())}.log', 
                   level=logging.INFO, format='%(asctime)s %(message)s')

def safe_copy(src, dst):
    try:
        if src.is_file():
            shutil.copy2(src, dst, follow_symlinks=False)
            logging.info(f"Copied: {src} -> {dst}")
        elif src.is_dir():
            dst.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        logging.error(f"Failed {src}: {e}")

def sync_level(depth=0, max_depth=3):
    """Batch sync by directory depth to avoid NTFS recursion freeze"""
    count = 0
    for root, dirs, files in os.walk(source, topdown=True):
        rel_path = root.relative_to(source)
        depth_now = len(rel_path.parts)
        
        if depth_now > max_depth:
            dirs[:] = []  # Prune deeper recursion
            continue
            
        dest_root = backup / rel_path
        for file in files:
            safe_copy(root / file, dest_root / file)
            count += 1
            
        if count % 100 == 0:
            print(f"Processed {count} files at depth {depth_now}")
            
        time.sleep(0.01)  # Yield to prevent I/O starvation
    
    # Delete extras in backup
    for root, dirs, files in os.walk(backup):
        rel_path = root.relative_to(backup)
        src_equiv = source / rel_path
        if not src_equiv.exists():
            shutil.rmtree(root)
            logging.info(f"Deleted: {root}")

if __name__ == "__main__":
    # print("DRY RUN MODE - remove dry_run=True for real sync")
    sync_level(max_depth=2)  # Start shallow
    print("Check /tmp/sync-*.log then increase max_depth")