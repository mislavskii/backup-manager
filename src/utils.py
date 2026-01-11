import functools
import logging
import shutil
import os
import time


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


@retry_on_failure()
def remove_directory(path):
    """Remove a directory with retry logic"""
    shutil.rmtree(path)


@retry_on_failure()
def remove_file(path):
    """Remove a file with retry logic"""
    os.remove(path)