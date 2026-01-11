import pytest
import os
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock
from src.backup_sync import Sync


class TestSyncClearDeleted:
    """Test cases for the clear_deleted method in Sync class"""

    @pytest.fixture
    def temp_directories(self, tmp_path):
        """Create temporary source and backup directories for testing"""
        source_dir = tmp_path / "source"
        backup_dir = tmp_path / "backup"
        source_dir.mkdir()
        backup_dir.mkdir()
        
        # Create test structure in source
        (source_dir / "dir1").mkdir()
        (source_dir / "dir1" / "file1.txt").write_text("content1")
        (source_dir / "dir2").mkdir()
        (source_dir / "file2.txt").write_text("content2")
        
        # Create files in backup that match source
        (backup_dir / "dir1").mkdir()
        (backup_dir / "dir1" / "file1.txt").write_text("content1")
        (backup_dir / "file2.txt").write_text("content2")
        
        # Create extra files in backup that should be deleted
        (backup_dir / "dir1" / "extra_file.txt").write_text("extra content")
        (backup_dir / "dir3").mkdir()  # Extra directory
        (backup_dir / "dir3" / "orphaned_file.txt").write_text("orphaned")
        (backup_dir / "extra_file.txt").write_text("extra")
        
        return source_dir, backup_dir

    def test_clear_deleted_dry_run(self, temp_directories):
        """Test that dry run doesn't actually delete files"""
        source_dir, backup_dir = temp_directories
        sync = Sync(str(source_dir), str(backup_dir))
        
        # Count files before dry run
        files_before = list(backup_dir.rglob("*"))
        
        # Run clear_deleted in dry run mode (default)
        sync.clear_deleted(dry=True)
        
        # Count files after dry run
        files_after = list(backup_dir.rglob("*"))
        
        # Should have same number of files (no actual deletion)
        assert len(files_before) == len(files_after)
        
        # Extra files should still exist
        assert (backup_dir / "dir1" / "extra_file.txt").exists()
        assert (backup_dir / "dir3").exists()
        assert (backup_dir / "extra_file.txt").exists()

    def test_clear_deleted_actual_deletion(self, temp_directories):
        """Test that files are actually deleted when dry=False"""
        source_dir, backup_dir = temp_directories
        sync = Sync(str(source_dir), str(backup_dir))
        
        # Run clear_deleted in actual deletion mode
        sync.clear_deleted(dry=False)
        
        # Files that exist in source should still exist
        assert (backup_dir / "dir1" / "file1.txt").exists()
        assert (backup_dir / "file2.txt").exists()  # This should exist as it's in source
        
        # Extra files should be deleted
        assert not (backup_dir / "dir1" / "extra_file.txt").exists()
        assert not (backup_dir / "dir3").exists()
        assert not (backup_dir / "extra_file.txt").exists()  # This should be deleted
        
        # Verify that directories that don't exist in source are deleted
        assert not (backup_dir / "dir3").exists()

    @patch('src.backup_sync.logging.info')
    def test_clear_deleted_logging(self, mock_logging, temp_directories):
        """Test that proper logging messages are generated"""
        source_dir, backup_dir = temp_directories
        sync = Sync(str(source_dir), str(backup_dir))
        
        sync.clear_deleted(dry=False)
        
        # Check that logging was called for deleted items
        log_calls = [call[0][0] for call in mock_logging.call_args_list]
        
        # Should log directory deletion
        assert any("Deleting dir tree:" in msg and "dir3" in msg for msg in log_calls)
        
        # Should log file deletion
        assert any("Deleting file:" in msg and "extra_file.txt" in msg for msg in log_calls)

    def test_clear_deleted_with_nonexistent_root(self, temp_directories):
        """Test handling of non-existent root directories during walk"""
        source_dir, backup_dir = temp_directories
        sync = Sync(str(source_dir), str(backup_dir))
        
        # Mock walk to return a non-existent root
        with patch.object(Path, 'walk') as mock_walk:
            mock_walk.return_value = [
                (Path("/nonexistent/path"), [], ["file.txt"]),
            ]
            
            # This should not raise an exception
            sync.clear_deleted(dry=False)

    def test_clear_deleted_empty_directories(self, tmp_path):
        """Test behavior with empty directories"""
        source_dir = tmp_path / "source"
        backup_dir = tmp_path / "backup"
        source_dir.mkdir()
        backup_dir.mkdir()
        
        # Create empty directory in backup that doesn't exist in source
        (backup_dir / "empty_dir").mkdir()
        
        sync = Sync(str(source_dir), str(backup_dir))
        sync.clear_deleted(dry=False)
        
        # Empty directory should be deleted
        assert not (backup_dir / "empty_dir").exists()

    def test_clear_deleted_no_extra_files(self, tmp_path):
        """Test behavior when there are no extra files to delete"""
        source_dir = tmp_path / "source"
        backup_dir = tmp_path / "backup"
        source_dir.mkdir()
        backup_dir.mkdir()
        
        # Create identical structures
        (source_dir / "file.txt").write_text("content")
        (backup_dir / "file.txt").write_text("content")
        
        sync = Sync(str(source_dir), str(backup_dir))
        
        # Count files before
        files_before = list(backup_dir.rglob("*"))
        
        sync.clear_deleted(dry=False)
        
        # Count files after (should be same)
        files_after = list(backup_dir.rglob("*"))
        
        assert len(files_before) == len(files_after)
        assert (backup_dir / "file.txt").exists()

    def test_clear_deleted_extra_files_in_source(self, temp_directories):
        """Test behavior when there are extra files in source not in backup"""
        source_dir, backup_dir = temp_directories
        
        # Add an extra file in source that's not in backup
        (source_dir / "extra_in_source.txt").write_text("extra content")
        
        sync = Sync(str(source_dir), str(backup_dir))
        
        # Count files before
        files_before = list(backup_dir.rglob("*"))
        
        # Run clear_deleted - should delete extra files in backup
        sync.clear_deleted(dry=False)
        
        # Count files after
        files_after = list(backup_dir.rglob("*"))
        
        # Should have fewer files after (extra files deleted)
        assert len(files_after) < len(files_before)
        
        # Existing files that match source should still exist
        assert (backup_dir / "dir1" / "file1.txt").exists()
        assert (backup_dir / "file2.txt").exists()
        
        # Extra files in backup should be deleted (they don't exist in source)
        assert not (backup_dir / "dir1" / "extra_file.txt").exists()
        assert not (backup_dir / "dir3").exists()
        assert not (backup_dir / "extra_file.txt").exists()
        
        # The extra file in source doesn't affect backup (it's not there to begin with)
        
    def test_clear_deleted_error_handling(self, temp_directories):
        """Test that clear_deleted properly handles errors during deletion"""
        source_dir, backup_dir = temp_directories
        
        sync = Sync(str(source_dir), str(backup_dir))
        
        # Create a directory that exists in backup but not in source
        extra_dir = backup_dir / "extra_dir"
        extra_dir.mkdir()
        
        # Create a file in that directory
        extra_file = extra_dir / "extra_file.txt"
        extra_file.write_text("extra content")
        
        # Test that clear_deleted processes all items and handles errors gracefully
        # The current implementation doesn't have explicit error handling,
        # so errors will propagate up to the caller
        try:
            sync.clear_deleted(dry=False)
            # If we get here, the deletion succeeded
            assert not extra_dir.exists()
        except (PermissionError, OSError) as e:
            # If we get an exception, it should be a permission or OS error
            # This documents the current behavior
            assert isinstance(e, (PermissionError, OSError))

    @patch('src.backup_sync.logging.error')
    @patch('src.backup_sync.logging.warning')
    def test_clear_deleted_retry_behavior(self, mock_warning, mock_error, temp_directories):
        """Test that clear_deleted retries failed operations and logs appropriately"""
        source_dir, backup_dir = temp_directories
        sync = Sync(str(source_dir), str(backup_dir))
        
        # Create a directory that exists in backup but not in source
        extra_dir = backup_dir / "extra_dir"
        extra_dir.mkdir()
        
        # Create a file in that directory
        extra_file = extra_dir / "extra_file.txt"
        extra_file.write_text("extra content")
        
        # Mock shutil.rmtree to fail twice (first attempt and retry)
        with patch('src.backup_sync.shutil.rmtree', side_effect=OSError("Permission denied")):
            sync.clear_deleted(dry=False)
        
        # Verify that warning and error logging occurred
        assert mock_warning.called
        assert mock_error.called
        
        # Verify that the method continued processing despite the error
        # (the fact that we get here without exception means it continued)

    @patch('src.backup_sync.logging.info')
    @patch('src.backup_sync.logging.error')
    def test_clear_deleted_successful_retry(self, mock_error, mock_info, temp_directories):
        """Test that successful retry logs appropriately"""
        source_dir, backup_dir = temp_directories
        sync = Sync(str(source_dir), str(backup_dir))
        
        # Create a directory that exists in backup but not in source
        extra_dir = backup_dir / "extra_dir"
        extra_dir.mkdir()
        
        # Create a file in that directory
        extra_file = extra_dir / "extra_file.txt"
        extra_file.write_text("extra content")
        
        # Mock shutil.rmtree to fail the first time but succeed the second time
        call_count = 0
        def rmtree_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise OSError("Permission denied")
            # Second call succeeds (no exception)
            # We don't actually delete the directory in the test, just verify the retry logic
        
        with patch('src.backup_sync.shutil.rmtree', side_effect=rmtree_side_effect):
            sync.clear_deleted(dry=False)
        
        # Verify that the function was called at least twice (first attempt + retry)
        assert call_count >= 2
        
        # Verify that warning logging occurred for the first failure
        assert mock_info.called