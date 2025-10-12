import sqlite3
import pytest

@pytest.fixture
def db_connection():
    conn = sqlite3.connect(":memory:")
    # Enable foreign key support
    conn.execute("PRAGMA foreign_keys = ON;")
    with open("db/artifact_miner_schema.sql") as f:
        conn.executescript(f.read())
    yield conn
    conn.close()

def test_project_table_insert_and_query(db_connection):
    cursor = db_connection.cursor()
    # Insert a new project into the Project table
    cursor.execute("INSERT INTO Project (name, description) VALUES (?, ?)", ("Test Project", "A test project"))
    db_connection.commit()

    # Query the project by name to verify insertion
    cursor.execute("SELECT * FROM Project WHERE name = ?", ("Test Project",))
    row = cursor.fetchone()
    # Ensure a row was returned
    assert row is not None
    # Check that the name and description match what was inserted
    assert row[1] == "Test Project"
    assert row[2] == "A test project"

def test_artifact_table_insert_and_query(db_connection):
    cursor = db_connection.cursor()
    # Insert a project for FK
    cursor.execute("INSERT INTO Project (name, description) VALUES (?, ?)", ("Proj1", "desc"))
    project_id = cursor.lastrowid
    # Insert artifact
    cursor.execute("INSERT INTO Artifact (project_id, path, type) VALUES (?, ?, ?)", (project_id, "/path/to/file.py", "code"))
    db_connection.commit()
    cursor.execute("SELECT * FROM Artifact WHERE path = ?", ("/path/to/file.py",))
    row = cursor.fetchone()
    assert row is not None
    assert row[1] == project_id
    assert row[2] == "/path/to/file.py"
    assert row[3] == "code"

def test_contribution_table_insert_and_query(db_connection):
    cursor = db_connection.cursor()
    # Insert project and artifact
    cursor.execute("INSERT INTO Project (name, description) VALUES (?, ?)", ("Proj2", "desc"))
    project_id = cursor.lastrowid
    cursor.execute("INSERT INTO Artifact (project_id, path, type) VALUES (?, ?, ?)", (project_id, "/file2.py", "code"))
    artifact_id = cursor.lastrowid
    # Insert contribution
    cursor.execute("INSERT INTO Contribution (project_id, artifact_id, activity_type, description) VALUES (?, ?, ?, ?)", (project_id, artifact_id, "code", "Initial commit"))
    db_connection.commit()
    cursor.execute("SELECT * FROM Contribution WHERE activity_type = ?", ("code",))
    row = cursor.fetchone()
    assert row is not None
    assert row[1] == project_id
    assert row[2] == artifact_id
    assert row[3] == "code"
    assert row[5] == "Initial commit"

def test_skill_and_projectskill_tables(db_connection):
    cursor = db_connection.cursor()
    # Insert project
    cursor.execute("INSERT INTO Project (name, description) VALUES (?, ?)", ("Proj3", "desc"))
    project_id = cursor.lastrowid
    # Insert skills
    cursor.execute("INSERT INTO Skill (name) VALUES (?)", ("Python",))
    skill_id1 = cursor.lastrowid
    cursor.execute("INSERT INTO Skill (name) VALUES (?)", ("SQL",))
    skill_id2 = cursor.lastrowid
    # Link skills to project
    cursor.execute("INSERT INTO ProjectSkill (project_id, skill_id) VALUES (?, ?)", (project_id, skill_id1))
    cursor.execute("INSERT INTO ProjectSkill (project_id, skill_id) VALUES (?, ?)", (project_id, skill_id2))
    db_connection.commit()
    # Query
    cursor.execute("SELECT Skill.name FROM Skill JOIN ProjectSkill ON Skill.id = ProjectSkill.skill_id WHERE ProjectSkill.project_id = ?", (project_id,))
    skills = {row[0] for row in cursor.fetchall()}
    assert skills == {"Python", "SQL"}

def test_foreign_key_cascade_delete(db_connection):
    cursor = db_connection.cursor()
    # Insert project, artifact, skill, projectskill
    cursor.execute("INSERT INTO Project (name, description) VALUES (?, ?)", ("Proj4", "desc"))
    project_id = cursor.lastrowid
    cursor.execute("INSERT INTO Artifact (project_id, path, type) VALUES (?, ?, ?)", (project_id, "/file3.py", "code"))
    cursor.execute("INSERT INTO Skill (name) VALUES (?)", ("Django",))
    skill_id = cursor.lastrowid
    cursor.execute("INSERT INTO ProjectSkill (project_id, skill_id) VALUES (?, ?)", (project_id, skill_id))
    db_connection.commit()
    # Delete project, check cascade
    cursor.execute("DELETE FROM Project WHERE id = ?", (project_id,))
    db_connection.commit()
    cursor.execute("SELECT * FROM Artifact WHERE project_id = ?", (project_id,))
    assert cursor.fetchone() is None
    cursor.execute("SELECT * FROM ProjectSkill WHERE project_id = ?", (project_id,))
    assert cursor.fetchone() is None
