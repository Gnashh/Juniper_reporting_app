"""
User Database Module
======================
CRUD operations for users.
Users store username, password, full name, email, is_admin, created_at, last_login.
"""

import mysql.connector
from db.connect_to_db import connect_to_db
import bcrypt
from datetime import datetime

def hash_password(password):
    """Hash a password using bcrypt"""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')

def verify_password(password, password_hash):
    """Verify a password against its hash"""
    return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))

def create_user(username, password, full_name=None, email=None, is_admin=False):
    """Create a new user"""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    password_hash = hash_password(password)
    
    try:
        cursor.execute(
            """INSERT INTO users (username, password_hash, full_name, email, is_admin) 
               VALUES (%s, %s, %s, %s, %s)""",
            (username, password_hash, full_name, email, is_admin)
        )
        conn.commit()
        user_id = cursor.lastrowid
        conn.close()
        return user_id
    except mysql.connector.IntegrityError:
        conn.close()
        raise Exception("Username already exists")

def authenticate_user(username, password):
    """Authenticate a user with username and password"""
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute(
        "SELECT * FROM users WHERE username = %s AND is_active = TRUE",
        (username,)
    )
    user = cursor.fetchone()
    
    if user and verify_password(password, user['password_hash']):
        # Update last login time
        cursor.execute(
            "UPDATE users SET last_login = %s WHERE id = %s",
            (datetime.now(), user['id'])
        )
        conn.commit()
        conn.close()
        return user
    
    conn.close()
    return None

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_user_by_username(username):
    """Get user by username"""
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
    user = cursor.fetchone()
    conn.close()
    return user

def get_all_users():
    """Get all users"""
    conn = connect_to_db()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, username, full_name, email, is_active, is_admin, created_at, last_login FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

def update_user(user_id, full_name=None, email=None, is_active=None, is_admin=None):
    """Update user information"""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if full_name is not None:
        updates.append("full_name = %s")
        params.append(full_name)
    if email is not None:
        updates.append("email = %s")
        params.append(email)
    if is_active is not None:
        updates.append("is_active = %s")
        params.append(is_active)
    if is_admin is not None:
        updates.append("is_admin = %s")
        params.append(is_admin)
    
    if updates:
        params.append(user_id)
        query = f"UPDATE users SET {', '.join(updates)} WHERE id = %s"
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()

def change_password(user_id, new_password):
    """Change user password"""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    password_hash = hash_password(new_password)
    cursor.execute(
        "UPDATE users SET password_hash = %s WHERE id = %s",
        (password_hash, user_id)
    )
    conn.commit()
    conn.close()

def delete_user(user_id):
    """Delete a user"""
    conn = connect_to_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
    conn.commit()
    conn.close()

