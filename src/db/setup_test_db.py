import psycopg2

def create_tables():
    try:
        # Connect to PostgreSQL
        connection = psycopg2.connect(
            host="localhost",
            port="5432",
            user="postgres",
            password="password",
            database="postgres"
        )
        cursor = connection.cursor()

        # Drop tables in dependency order
        cursor.execute("DROP TABLE IF EXISTS artifacts CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS category CASCADE;")
        cursor.execute("DROP TABLE IF EXISTS users CASCADE;")

        # Users table
        create_users_table = '''
        CREATE TABLE users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            email VARCHAR(100) UNIQUE, -- optional but common
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        '''

        # Category table
        create_category_table = '''
        CREATE TABLE category (
            id SERIAL PRIMARY KEY,
            main_category VARCHAR(100) UNIQUE NOT NULL,
            description TEXT DEFAULT 'No description provided.'
        );
        '''

        # Artifacts table
        create_artifacts_table = '''
        CREATE TABLE artifacts (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            category_id INTEGER,
            file_name VARCHAR(255) NOT NULL,
            file_path TEXT NOT NULL,
            file_type VARCHAR(50),
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            CONSTRAINT fk_user
                FOREIGN KEY (user_id)
                REFERENCES users (id)
                ON DELETE CASCADE,

            CONSTRAINT fk_category
                FOREIGN KEY (category_id)
                REFERENCES category (id)
                ON DELETE SET NULL,

            CONSTRAINT uq_user_file
                UNIQUE (user_id, file_name) -- prevents duplicate filenames per user
        );
        '''

        # Execute table creation
        cursor.execute(create_users_table)
        cursor.execute(create_category_table)
        cursor.execute(create_artifacts_table)

        # Insert default categories if none exist
        cursor.execute("SELECT COUNT(*) FROM category;")
        count = cursor.fetchone()[0]

        if count == 0:
            cursor.executemany(
                "INSERT INTO category (main_category) VALUES (%s);",
                [
                    ("General Cat 1",), ("General Cat 2",), ("General Cat 3",),
                    ("General Cat 4",), ("General Cat 5",), ("General Cat 6",),
                    ("General Cat 7",), ("General Cat 8",), ("General Cat 9",),
                    ("General Cat 10",)
                ]
            )
            print("Inserted 10 default categories.")
        else:
            print("Categories already exist, skipping insert.")

        connection.commit()
        print("Tables and relationships created successfully!")

    except Exception as e:
        print("Failed to create tables:", e)

    finally:
        if cursor:
            cursor.close()
        if connection:
            connection.close()


if __name__ == "__main__":
    create_tables()
