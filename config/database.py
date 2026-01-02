"""
Database Configuration
Supports SQLite and PostgreSQL dual backends
"""
import os

class DatabaseConfig:
    DB_TYPE = 'sqlite'  # 'sqlite' or 'postgresql'

    # SQLite config (uses paths.py)
    @property
    def SQLITE_PATH(self):
        from config.paths import paths
        return paths.db_path

    # PostgreSQL config
    PG_HOST = 'localhost'
    PG_PORT = 5432
    PG_USER = 'stock_user'
    PG_PASSWORD = 'stock_password'
    PG_DATABASE = 'stock_db'
    PG_CONNECT_TIMEOUT = 30

    @classmethod
    def switch_to_postgresql(cls):
        """Switch to PostgreSQL backend"""
        cls.DB_TYPE = 'postgresql'
        print(f"✓ Switched to: {cls.DB_TYPE}")

    @classmethod
    def switch_to_sqlite(cls):
        """Switch to SQLite backend"""
        cls.DB_TYPE = 'sqlite'
        print(f"✓ Switched to: {cls.DB_TYPE}")

    @classmethod
    def get_connection_string(cls):
        """Return connection string for current backend"""
        if cls.DB_TYPE == 'postgresql':
            return f"host={cls.PG_HOST} port={cls.PG_PORT} dbname={cls.PG_DATABASE} " \
                   f"user={cls.PG_USER} password={cls.PG_PASSWORD} connect_timeout={cls.PG_CONNECT_TIMEOUT}"
        else:
            return cls().SQLITE_PATH

# Global instance
config = DatabaseConfig()
