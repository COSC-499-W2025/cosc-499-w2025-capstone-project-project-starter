import psycopg2


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

        # Create category table (just main categories for now)
        create_category_table = '''
        CREATE TABLE IF NOT EXISTS category (
            id SERIAL PRIMARY KEY,
            main_category VARCHAR(100) NOT NULL
        );
        '''

        # Execute all table creation queries
        cursor.execute(create_users_table)
        cursor.execute(create_artifacts_table)
        cursor.execute(create_category_table)

        # Commit the changes
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
