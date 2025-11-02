import psycopg2
from connect import connect_to_postgres


def create_tables():
    try:
        # Connect to the PostgreSQL database
        connection = psycopg2.connect(
            host="localhost",
            port="5432",
            user="postgres",
            password="password",
            database="postgres"
        )
        cursor = connection.cursor()

        # Create users table
        create_users_table = '''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        '''

        # Create artifacts table
        create_artifacts_table = '''
        CREATE TABLE IF NOT EXISTS artifacts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            file_name VARCHAR(255) NOT NULL,
            file_path TEXT NOT NULL,
            file_type VARCHAR(50)
        );
        '''

        # Create category table
        create_category_table = '''
        CREATE TABLE IF NOT EXISTS category (
            id SERIAL PRIMARY KEY,
            main_category VARCHAR(100) UNIQUE NOT NULL
        );
        '''

        # Execute table creation
        cursor.execute(create_users_table)
        cursor.execute(create_artifacts_table)
        cursor.execute(create_category_table)

        # Check if the category table is empty
        cursor.execute("SELECT COUNT(*) FROM category;")
        count = cursor.fetchone()[0]

        if count == 0:
            # Insert 10 default categories
            cursor.executemany(
                "INSERT INTO category (main_category) VALUES (%s);",
                [
                    ("General Cat 1",),
                    ("General Cat 2",),
                    ("General Cat 3",),
                    ("General Cat 4",),
                    ("General Cat 5",),
                    ("General Cat 6",),
                    ("General Cat 7",),
                    ("General Cat 8",),
                    ("General Cat 9",),
                    ("General Cat 10",)
                ]
            )
            print("Inserted default categories into 'category' table.")
        else:
            print("Category table already has data. Skipping insertion.")

        # Commit all changes
        connection.commit()
        print("Tables created successfully!")

    except Exception as e:
        print("Failed to create tables:", e)

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


if __name__ == "__main__":
    create_tables()
