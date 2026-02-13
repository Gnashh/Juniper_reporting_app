import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def connect_to_db():
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database=os.getenv('DB_NAME', 'internship'),
            user=os.getenv('DB_USER', 'root'),
            password=os.getenv('DB_PASSWORD'),
            port=int(os.getenv('DB_PORT', 3306)),
            connection_timeout=3,
            autocommit=True
        )
        if connection.is_connected():
            return connection
        else:
            raise Exception("Connection established but not active")
            
    except Error as e:
        if e.errno == 2003:
            raise Exception("Database server not accessible")
        elif e.errno == 1045:
            raise Exception("Access denied - check username/password")
        elif e.errno == 1049:
            raise Exception(f"Database does not exist")
        else:
            raise Exception(f"Database error: {e}")

# ✅ CRITICAL: No code here that calls connect_to_db()!
# ✅ Everything must be inside functions or inside if __name__ == "__main__"

# ONLY for testing when run directly (not when imported)
if __name__ == "__main__":
    # This is safe - only runs when you do: python connect_to_db.py
    print("Testing database connection...")
    try:
        conn = connect_to_db()
        print("✅ Connection successful!")
        conn.close()
    except Exception as e:
        print(f"❌ Connection failed: {e}")
