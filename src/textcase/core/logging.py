"""
Logging configuration for textcase core modules.
"""
from datetime import datetime
import glob
import logging
from logging.handlers import RotatingFileHandler
import os
from typing import Optional


def setup_logging(verbose: bool = False) -> None:
    """
    Configure application logging with timestamped files and rotation.
    
    Args:
        verbose: Whether to enable verbose logging to console
    """
    # Create logs directory in user's home .textcase directory
    log_dir = os.path.expanduser("~/.textcase/logs")
    os.makedirs(log_dir, exist_ok=True)

    # Generate timestamp for log filename
    timestamp = datetime.utcnow().strftime("%Y-%m-%d-%H-%M-%S-%f")[:23]
    log_file = os.path.join(log_dir, f"{timestamp}.log")

    # Configure rotating file handler
    # Keep up to 50 log files, max 1MB each
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=1024*1024,  # 1MB
        backupCount=49,  # Keep 50 files total (current + 49 backups)
        encoding='utf-8'
    )
    
    # Set up formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Always log DEBUG to file
    root_logger.addHandler(file_handler)
    
    # Configure console handler if verbose is enabled
    if verbose:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # Clean up old logs if we have too many
    cleanup_old_logs(log_dir, max_logs=50)


def cleanup_old_logs(log_dir: str, max_logs: int) -> None:
    """
    Remove oldest log files if we exceed maximum count.
    
    Args:
        log_dir: Directory containing log files
        max_logs: Maximum number of log files to keep
    """
    log_files = glob.glob(os.path.join(log_dir, "*.log*"))
    log_files.sort(key=os.path.getctime)  # Sort by creation time

    # Remove oldest files if we have too many
    while len(log_files) > max_logs:
        try:
            os.remove(log_files.pop(0))  # Remove oldest file
        except OSError:
            pass  # Ignore errors removing old logs


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: Name of the logger, typically the module name
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
