import psycopg2

def connect_to_postgres():
    try:
        connection = psycopg2.connect(
            host="localhost",
            port="5432",
            user="postgres",        # change if you made a different user
            password="password",    # use the password you set during installation
            database="postgres"     # use the default postgres db for now
        )
        print("Connection successful!")
        connection.close()
    except Exception as e:
        print("Connection failed:", e)


if __name__ == "__main__":
    connect_to_postgres()
