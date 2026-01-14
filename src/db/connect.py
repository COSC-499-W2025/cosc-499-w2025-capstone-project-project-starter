# src/db/connect.py (updated)
import psycopg2
import os
import time

def get_db_connection(max_retries=5, retry_delay=2):
    """Get and return an open database connection with retry logic"""
    
    # Determine connection parameters based on environment
    # Inside Docker: connect to service name 'db'
    # Outside Docker: connect to localhost
    
    for attempt in range(max_retries):
        try:
            # Try different connection parameters in order
            connection_params_list = [
                # Docker environment (app container connecting to db container)
                {
                    "host": "db",
                    "port": "5432",
                    "user": "postgres",
                    "password": "postgres",
                    "database": "postgres"
                },
                # Local development (outside Docker)
                {
                    "host": "localhost",
                    "port": "5432",
                    "user": "postgres",
                    "password": "postgres",
                    "database": "postgres"
                }
            ]
            
            for params in connection_params_list:
                try:
                    print(f"Attempting connection to {params['host']}:{params['port']}...")
                    connection = psycopg2.connect(**params)
                    print(f"✅ Connected to database at {params['host']}:{params['port']}")
                    return connection
                except psycopg2.OperationalError as e:
                    print(f"Failed to connect to {params['host']}: {e}")
                    continue
            
            raise Exception("All connection attempts failed")
            
        except Exception as e:
            print(f"Database connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt < max_retries - 1:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("Max retries reached. Could not connect to database.")
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