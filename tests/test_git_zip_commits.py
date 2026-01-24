import tempfile
import zipfile
import shutil
import os
from git import Repo, InvalidGitRepositoryError

from src.api.ingest import extract_commits_from_git_zip


# -----------------------------
# Helper: create a zipped Git repo
# -----------------------------
def create_git_repo_zip(zip_path: str):
    tmpdir = tempfile.mkdtemp()  # temp dir for repo
    try:
        # Init repo with initial_branch = main to ensure consistency across systems
        repo = Repo.init(tmpdir, initial_branch='main')

        # Add a file and commit
        file_path = os.path.join(tmpdir, "file.txt")
        with open(file_path, "w") as f:
            f.write("hello")
        repo.index.add(["file.txt"])
        repo.index.commit("initial commit")

        # Zip the folder INCLUDING .git
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(tmpdir):
                for file in files:
                    abs_path = os.path.join(root, file)
                    rel_path = os.path.relpath(abs_path, tmpdir)
                    zf.write(abs_path, rel_path)
    finally:
        # Cleanup temp repo folder
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)


# -----------------------------
# Test
# -----------------------------
def test_extract_commits_from_git_zip():
    tmpzip_path = os.path.join(tempfile.gettempdir(), "tmp_git_repo.zip")
    create_git_repo_zip(tmpzip_path)

    commits = extract_commits_from_git_zip(tmpzip_path)
    assert commits == ["initial commit"]

    os.remove(tmpzip_path)  # cleanup