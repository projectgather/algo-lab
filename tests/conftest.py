import pytest


@pytest.fixture(autouse=True)
def progression_db_isolee(tmp_path, monkeypatch):
    monkeypatch.setenv("ALGOLAB_DB_PATH", str(tmp_path / "progression.sqlite3"))