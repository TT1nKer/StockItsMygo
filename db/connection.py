"""
Database Connection Manager
Unifies SQLite and PostgreSQL syntax differences
"""
import sqlite3
import psycopg2
import psycopg2.extras
from config.database import config

class DatabaseConnection:
    """Database connection manager with syntax abstraction"""

    def __init__(self):
        pass

    @property
    def db_type(self):
        """Dynamically get current database type"""
        return config.DB_TYPE

    def connect(self):
        """
        Create database connection

        Returns:
            Connection object (sqlite3.Connection or psycopg2.connection)
        """
        if self.db_type == 'sqlite':
            conn = sqlite3.connect(config.get_connection_string())
            conn.execute('PRAGMA foreign_keys = ON')
            return conn
        else:  # PostgreSQL
            conn = psycopg2.connect(config.get_connection_string())
            conn.set_session(autocommit=False)
            return conn

    def get_placeholder(self, n=1):
        """
        Return placeholder string for parameterized queries

        Args:
            n: Number of placeholders

        Returns:
            SQLite: '?, ?, ?'
            PostgreSQL: '%s, %s, %s'
        """
        if self.db_type == 'sqlite':
            return ', '.join(['?'] * n)
        else:
            return ', '.join(['%s'] * n)

    def insert_or_replace(self, table, columns, conflict_columns=None):
        """
        Generate INSERT OR REPLACE statement

        Args:
            table: Table name
            columns: Column list ['col1', 'col2', 'col3']
            conflict_columns: Conflict key(s) ['id'] or ['symbol', 'date']
                            If None, uses first column

        Returns:
            SQL statement template (string)

        Example:
            SQLite: INSERT OR REPLACE INTO stocks (symbol, name) VALUES (?, ?)
            PostgreSQL: INSERT INTO stocks (symbol, name) VALUES (%s, %s)
                       ON CONFLICT (symbol) DO UPDATE SET name = EXCLUDED.name
        """
        if conflict_columns is None:
            conflict_columns = [columns[0]]

        placeholders = self.get_placeholder(len(columns))
        cols_str = ', '.join(columns)

        if self.db_type == 'sqlite':
            return f"INSERT OR REPLACE INTO {table} ({cols_str}) VALUES ({placeholders})"

        else:  # PostgreSQL
            conflict_str = ', '.join(conflict_columns)

            # Generate UPDATE clause (exclude conflict columns)
            update_cols = [col for col in columns if col not in conflict_columns]

            if update_cols:
                updates = ', '.join([f"{col} = EXCLUDED.{col}" for col in update_cols])
                return f"""
                    INSERT INTO {table} ({cols_str})
                    VALUES ({placeholders})
                    ON CONFLICT ({conflict_str}) DO UPDATE SET {updates}
                """
            else:
                # All columns are primary key, only insert
                return f"""
                    INSERT INTO {table} ({cols_str})
                    VALUES ({placeholders})
                    ON CONFLICT ({conflict_str}) DO NOTHING
                """

    def create_index(self, index_name, table, columns, unique=False):
        """
        Create index (handles IF NOT EXISTS syntax)

        Args:
            index_name: Index name
            table: Table name
            columns: Column list ['col1', 'col2']
            unique: Create unique index

        Returns:
            SQL statement (string)
        """
        unique_str = 'UNIQUE ' if unique else ''
        cols_str = ', '.join(columns)
        return f"CREATE {unique_str}INDEX IF NOT EXISTS {index_name} ON {table} ({cols_str})"

    def get_autoincrement_type(self):
        """
        Return auto-increment field type

        Returns:
            SQLite: 'INTEGER PRIMARY KEY AUTOINCREMENT'
            PostgreSQL: 'SERIAL PRIMARY KEY'
        """
        if self.db_type == 'sqlite':
            return 'INTEGER PRIMARY KEY AUTOINCREMENT'
        else:
            return 'SERIAL PRIMARY KEY'

    def convert_query_placeholders(self, query):
        """
        Convert SQLite-style placeholders (?) to PostgreSQL-style (%s)

        Args:
            query: SQL query string with ? placeholders

        Returns:
            Query with appropriate placeholders for current database type
        """
        if self.db_type == 'postgresql':
            return query.replace('?', '%s')
        return query

# Global connection manager
db_connection = DatabaseConnection()
