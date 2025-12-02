import time
import sys
import os
import psycopg2
from psycopg2 import OperationalError

DB_HOST = "db" # The service name of the postgres container
DB_NAME = os.environ.get("POSTGRES_DB", "postgres")
DB_USER = os.environ.get("POSTGRES_USER", "postgres")
DB_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "postgres")
MAX_RETRIES = 30 # Wait up to 30 seconds

def wait_for_db():
    print(f"Waiting for database at host: {DB_HOST}...")
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Attempt to connect
            conn = psycopg2.connect(
                host=DB_HOST,
                database=DB_NAME,
                user=DB_USER,
                password=DB_PASSWORD,
                connect_timeout=1
            )
            conn.close()
            print("Database is ready! Connection successful.")
            return True
        except OperationalError:
            print(f"Connection attempt {attempt}/{MAX_RETRIES} failed. Retrying in 1 second...")
            time.sleep(1)
    
    print("Error: Database connection failed after multiple retries.")
    sys.exit(1)

if __name__ == "__main__":
    wait_for_db()