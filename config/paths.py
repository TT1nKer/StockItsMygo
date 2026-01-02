"""
Cross-Platform Path Configuration
Auto-detects OS and provides correct paths
"""
import os
import platform

class PathConfig:
    """Platform-aware path configuration"""

    def __init__(self):
        self.platform = platform.system()  # 'Windows' or 'Darwin' (macOS)
        self.base_dir = self._get_base_dir()

    def _get_base_dir(self):
        """Get base directory based on platform"""
        if self.platform == 'Windows':
            return 'd:/strategy=Z'
        else:  # macOS/Linux
            # Get project root (2 levels up from this file)
            return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    @property
    def db_path(self):
        """Path to SQLite database"""
        return os.path.join(self.base_dir, 'db', 'stock.db')

    @property
    def data_dir(self):
        """Path to DATA directory"""
        return os.path.join(self.base_dir, 'DATA')

    @property
    def reports_dir(self):
        """Path to reports directory"""
        return os.path.join(self.base_dir, 'docs', 'reports')

    def nasdaq_csv(self):
        """Path to NASDAQ CSV file"""
        return os.path.join(self.data_dir, 'nasdaq-listed-symbols.csv')

# Global instance
paths = PathConfig()
