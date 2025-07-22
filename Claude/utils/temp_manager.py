"""
Temporary file management for PICO application.
"""
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional
import atexit
import logging

logger = logging.getLogger(__name__)

class TempFileManager:
    """Manager for temporary files and directories."""
    
    def __init__(self, temp_dir: Optional[str] = None):
        self.temp_dir = temp_dir or tempfile.mkdtemp(prefix="pico_")
        self.created_files: list = []
        self.created_dirs: list = []
        
        # Register cleanup on exit
        atexit.register(self.cleanup)
        
    def create_temp_file(self, suffix: str = "", prefix: str = "temp_") -> str:
        """Create a temporary file."""
        temp_file = tempfile.mktemp(suffix=suffix, prefix=prefix, dir=self.temp_dir)
        self.created_files.append(temp_file)
        logger.debug(f"Created temporary file: {temp_file}")
        return temp_file
        
    def create_temp_dir(self, suffix: str = "", prefix: str = "temp_") -> str:
        """Create a temporary directory."""
        temp_dir = tempfile.mkdtemp(suffix=suffix, prefix=prefix, dir=self.temp_dir)
        self.created_dirs.append(temp_dir)
        logger.debug(f"Created temporary directory: {temp_dir}")
        return temp_dir
        
    def cleanup(self):
        """Clean up all temporary files and directories."""
        # Remove files
        for file_path in self.created_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.debug(f"Removed temporary file: {file_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary file {file_path}: {e}")
                
        # Remove directories
        for dir_path in self.created_dirs:
            try:
                if os.path.exists(dir_path):
                    shutil.rmtree(dir_path)
                    logger.debug(f"Removed temporary directory: {dir_path}")
            except Exception as e:
                logger.warning(f"Failed to remove temporary directory {dir_path}: {e}")
                
        # Remove main temp directory
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
                logger.debug(f"Removed main temporary directory: {self.temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to remove main temporary directory {self.temp_dir}: {e}")

# Global temp manager instance
temp_manager = TempFileManager()