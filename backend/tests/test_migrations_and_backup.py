import os
import tempfile
from backend.app.services.migration_and_backup import generate_postgresql_and_sqlite_ddl, create_database_backup_json


def test_postgresql_and_sqlite_ddl_compilation():
    res = generate_postgresql_and_sqlite_ddl()
    assert res["tables_count"] == 10
    assert "CREATE TABLE educational_contexts" in res["postgresql_ddl"]
    assert "FOREIGN KEY(context_id) REFERENCES educational_contexts (id) ON DELETE CASCADE" in res["postgresql_ddl"]
    assert "TIMESTAMP WITH TIME ZONE" in res["postgresql_ddl"]


def test_backup_creation():
    with tempfile.TemporaryDirectory() as tmpdir:
        b_path = os.path.join(tmpdir, "backup_test.json")
        res = create_database_backup_json(b_path)
        assert os.path.isfile(b_path)
        assert res["backupVersion"] == "1.0"

