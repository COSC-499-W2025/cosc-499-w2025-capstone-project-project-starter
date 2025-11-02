import psycopg2
from connect import connect_to_postgres


def create_test_table():
    try:
        connection = psycopg2.connect(
            host="localhost",
            port="5432",
            user="postgres",
            password="password",
            database="postgres"
        )
        cursor = connection.cursor()
        create_table_query = '''
        CREATE TABLE IF NOT EXISTS test_table (
            id SERIAL PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        );
        '''
        cursor.execute(create_table_query)
        connection.commit()
        print("Test table created successfully!")
    except Exception as e:
        print("Failed to create test table:", e)
    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()




if __name__ == "__main__":
    create_test_table()