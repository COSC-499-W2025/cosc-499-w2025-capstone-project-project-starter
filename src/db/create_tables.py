import psycopg2
from connect import connect_to_postgres


def create_tables():
    try:
        # Connect to the PostgreSQL database
        connection = psycopg2.connect(
            host="postgres_db",
            port="5432",
            user="postgres",
            password="password",
            database="postgres"
        )
        cursor = connection.cursor()

        # Drop existing tables (optional but helps reset structure)
        cursor.execute("DROP TABLE IF EXISTS artifacts CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS users CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS category CASCADE;")

        # Create users table
        create_users_table = '''
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
        '''

        # Create category table
        create_category_table = '''
        CREATE TABLE IF NOT EXISTS category (
            id SERIAL PRIMARY KEY,
            main_category VARCHAR(100) UNIQUE NOT NULL
        );
        '''

        # Create artifacts table (linked to users + category)
        create_artifacts_table = '''
        CREATE TABLE IF NOT EXISTS artifacts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            category_id INTEGER REFERENCES category(id) ON DELETE SET NULL,
            file_name VARCHAR(255) NOT NULL,
            file_path TEXT NOT NULL,
            file_type VARCHAR(50)
        );
        '''

        # Execute table creation
        cursor.execute(create_users_table)
        cursor.execute(create_category_table)
        cursor.execute(create_artifacts_table)

        # Insert 10 default categories (only if empty)
        cursor.execute("SELECT COUNT(*) FROM category;")
        count = cursor.fetchone()[0]

        if count == 0:
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
            print("Inserted 10 default categories into 'category' table.")
        else:
            print("Category table already has data. Skipping insertion.")

        # Commit all changes
        connection.commit()
        print("Tables and relationships created successfully!")

    except Exception as e:
        print("Failed to create tables:", e)

    finally:
        try:
            if cursor:
                cursor.close()
        except NameError:
            pass
        try:
            if connection:
                connection.close()
        except NameError:
            pass


if __name__ == "__main__":
    create_tables()