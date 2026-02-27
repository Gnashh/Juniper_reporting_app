"""
Setup script for authentication system
Run this script to create the users table and add the default admin user
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db.connect_to_db import connect_to_db
from db.users import create_user, get_user_by_username
import mysql.connector

def create_users_table():
    """Create the users table if it doesn't exist"""
    conn = connect_to_db()
    cursor = conn.cursor()
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS users (
        id INT PRIMARY KEY AUTO_INCREMENT,
        username VARCHAR(50) UNIQUE NOT NULL,
        password_hash VARCHAR(255) NOT NULL,
        full_name VARCHAR(100),
        email VARCHAR(100),
        is_active BOOLEAN DEFAULT TRUE,
        is_admin BOOLEAN DEFAULT FALSE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP NULL,
        INDEX idx_username (username),
        INDEX idx_email (email)
    )
    """
    
    try:
        cursor.execute(create_table_sql)
        conn.commit()
        print("✅ Users table created successfully (or already exists)")
        return True
    except Exception as e:
        print(f"❌ Error creating users table: {e}")
        return False
    finally:
        conn.close()

def create_default_admin():
    """Create the default admin user if it doesn't exist"""
    try:
        # Check if admin user already exists
        existing_user = get_user_by_username('admin')
        
        if existing_user:
            print("ℹ️  Admin user already exists")
            print(f"   Username: admin")
            print(f"   You can login with the existing admin account")
            return True
        
        # Create admin user
        user_id = create_user(
            username='admin',
            password='admin123',
            full_name='Administrator',
            email='admin@example.com',
            is_admin=True
        )
        
        print("✅ Default admin user created successfully!")
        print(f"   Username: admin")
        print(f"   Password: admin123")
        print(f"   ⚠️  IMPORTANT: Change this password after first login!")
        return True
        
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        return False

def main():
    print("=" * 60)
    print("Authentication System Setup")
    print("=" * 60)
    print()
    
    # Test database connection
    print("🔍 Testing database connection...")
    try:
        conn = connect_to_db()
        conn.close()
        print("✅ Database connection successful")
        print()
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print()
        print("Please check your .env file and database configuration")
        return
    
    # Create users table
    print("📋 Creating users table...")
    if not create_users_table():
        print()
        print("Setup failed. Please check the error messages above.")
        return
    print()
    
    # Create default admin user
    print("👤 Creating default admin user...")
    if not create_default_admin():
        print()
        print("Setup failed. Please check the error messages above.")
        return
    print()
    
    print("=" * 60)
    print("✅ Setup completed successfully!")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Run the app: streamlit run app.py")
    print("2. Login with username: admin, password: admin123")
    print("3. Change the admin password immediately")
    print("4. Create additional user accounts as needed")
    print()

if __name__ == "__main__":
    main()

