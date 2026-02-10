import mysql.connector
from mysql.connector import Error

def connect_to_db():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='internship',
            user='root',
            password='S9kx7A4a#gnash',
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
