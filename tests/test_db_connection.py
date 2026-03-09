import pytest
from src.config.db_config import get_connection


def test_connection():
    conn = get_connection()
    if conn is None:
        pytest.skip("Database not available (POSTGRES_* env or server not running)")
    print("Database connection is GOOD")
    conn.close()


if __name__ == "__main__":
    test_connection()
