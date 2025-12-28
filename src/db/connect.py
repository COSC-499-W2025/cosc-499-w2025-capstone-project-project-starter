# src/db/connect.py (updated)
import psycopg2
import os

def get_db_connection():
    """Get and return an open database connection"""
    try:
        connection = psycopg2.connect(
            host="localhost",  # Changed from "postgres_db" to "localhost" for host machine
            port="5432",
            user="postgres",
            password="postgres",
            database="postgres"
        )
        return connection
    except Exception as e:
        # Try localhost if postgres_db fails
        try:
            connection = psycopg2.connect(
                host="localhost",
                port="5432",
                user="postgres",
                password="postgres",
                database="postgres"
            )
            return connection
        except Exception as e2:
            print(f"Database connection failed: {e2}")
            raise

def connect_to_postgres():
    """Test connection (existing function)"""
    try:
        connection = get_db_connection()
        print("Connection successful!")
        connection.close()
    except Exception as e:
        print("Connection failed:", e)

if __name__ == "__main__":
    connect_to_postgres()