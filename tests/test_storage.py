import sqlite3
import pytest
from infra_monitor.storage import managed_connection


def test_managed_connection_commits_and_closes(tmp_path):
    db_path = tmp_path / "commit_test.db"
    connection = sqlite3.connect(db_path)

    with managed_connection(connection) as db:
        db.execute("CREATE TABLE test_data (value TEXT)")
        db.execute("INSERT INTO test_data VALUES ('success')")

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")

    with sqlite3.connect(db_path) as db:
        result = db.execute("SELECT value FROM test_data").fetchone()

    assert result[0] == "success"


def test_managed_connection_rolls_back_and_closes(tmp_path):
    db_path = tmp_path / "rollback_test.db"
    connection = sqlite3.connect(db_path)
    connection.execute("CREATE TABLE test_data (value TEXT)")
    connection.commit()

    with pytest.raises(RuntimeError):
        with managed_connection(connection) as db:
            db.execute("INSERT INTO test_data VALUES ('failure')")
            raise RuntimeError("Simulated database failure")

    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")

    with sqlite3.connect(db_path) as db:
        result = db.execute("SELECT COUNT(*) FROM test_data").fetchone()

    assert result[0] == 0
