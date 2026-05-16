"""
Authentication Module for Stock Recommendation System
Provides user registration, login, session management, and route protection.
"""

from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from werkzeug.security import generate_password_hash, check_password_hash
import psycopg2

from config.database import config

# Configuration
INVITATION_CODE = "stocktest2026"


def _db_conn():
    """Compute connection string lazily so env-var changes are picked up per call."""
    return config.get_connection_string()

# ============================================================================
# Password Management
# ============================================================================

def hash_password(password):
    """
    Hash password using werkzeug's secure PBKDF2-SHA256 hashing.

    Args:
        password (str): Plain text password

    Returns:
        str: Hashed password
    """
    return generate_password_hash(password, method='pbkdf2:sha256')


def verify_password(password, password_hash):
    """
    Verify password against stored hash.

    Args:
        password (str): Plain text password to verify
        password_hash (str): Stored password hash

    Returns:
        bool: True if password matches, False otherwise
    """
    return check_password_hash(password_hash, password)


# ============================================================================
# Session Management
# ============================================================================

def get_current_user_id():
    """
    Get current logged-in user ID from session.

    Returns:
        int or None: User ID if logged in, None otherwise
    """
    return session.get('user_id')


def get_current_username():
    """
    Get current logged-in username from session.

    Returns:
        str or None: Username if logged in, None otherwise
    """
    return session.get('username')


def is_logged_in():
    """
    Check if user is currently logged in.

    Returns:
        bool: True if user is logged in, False otherwise
    """
    return 'user_id' in session


# ============================================================================
# Route Protection Decorator
# ============================================================================

def login_required(f):
    """
    Decorator to require login for routes.

    For API routes (starting with /api/), returns JSON 401 error.
    For page routes, redirects to login page.

    Usage:
        @app.route('/protected')
        @login_required
        def protected_route():
            return "This requires login"
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            # For API routes, return JSON error
            if request.path.startswith('/api/'):
                return jsonify({'error': 'Authentication required'}), 401
            # For page routes, redirect to login
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================================
# User Registration
# ============================================================================

def register_user(username, password, invitation_code):
    """
    Register a new user.

    Args:
        username (str): Desired username (3-50 characters)
        password (str): Plain text password (min 8 characters)
        invitation_code (str): Invitation code for registration

    Returns:
        tuple: (success: bool, message: str, user_id: int or None)
    """
    # Validate invitation code
    if invitation_code != INVITATION_CODE:
        return (False, "Invalid invitation code", None)

    # Validate username
    if not username or len(username) < 3 or len(username) > 50:
        return (False, "Username must be 3-50 characters", None)

    # Validate password
    if not password or len(password) < 8:
        return (False, "Password must be at least 8 characters", None)

    # Hash password
    password_hash = hash_password(password)

    try:
        conn = psycopg2.connect(_db_conn())
        cursor = conn.cursor()

        # Check if username already exists
        cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            conn.close()
            return (False, "Username already taken", None)

        # Insert new user
        cursor.execute("""
            INSERT INTO users (username, password_hash, is_active)
            VALUES (%s, %s, true)
            RETURNING id
        """, (username, password_hash))

        user_id = cursor.fetchone()[0]
        conn.commit()
        conn.close()

        return (True, "Registration successful", user_id)

    except Exception as e:
        return (False, f"Registration failed: {str(e)}", None)


# ============================================================================
# User Authentication
# ============================================================================

def authenticate_user(username, password):
    """
    Authenticate a user with username and password.

    Args:
        username (str): Username
        password (str): Plain text password

    Returns:
        tuple: (success: bool, message: str, user_id: int or None)
    """
    try:
        conn = psycopg2.connect(_db_conn())
        cursor = conn.cursor()

        # Fetch user by username
        cursor.execute("""
            SELECT id, password_hash, is_active
            FROM users
            WHERE username = %s
        """, (username,))

        result = cursor.fetchone()

        if not result:
            conn.close()
            return (False, "Invalid username or password", None)

        user_id, password_hash, is_active = result

        # Check if account is active
        if not is_active:
            conn.close()
            return (False, "Account is inactive", None)

        # Verify password
        if not verify_password(password, password_hash):
            conn.close()
            return (False, "Invalid username or password", None)

        # Update last login timestamp
        cursor.execute("""
            UPDATE users
            SET last_login = CURRENT_TIMESTAMP
            WHERE id = %s
        """, (user_id,))
        conn.commit()
        conn.close()

        return (True, "Login successful", user_id)

    except Exception as e:
        return (False, f"Login failed: {str(e)}", None)
