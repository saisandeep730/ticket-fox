import pytest
from sqlalchemy.dialects import postgresql, sqlite
from sqlalchemy.schema import CreateTable

from app.database.models import Base, Watch


@pytest.mark.parametrize("dialect", [postgresql.dialect(), sqlite.dialect()])
def test_every_table_compiles_on_both_dialects(dialect):
    """A column type that one dialect cannot render would break ``init_db``."""
    for table in Base.metadata.tables.values():
        ddl = str(CreateTable(table).compile(dialect=dialect))
        assert f"CREATE TABLE {table.name}" in ddl


def test_watch_table_carries_the_columns_the_worker_writes():
    """Columns the polling worker and the add flow persist must exist on ``Watch``."""
    expected = {
        "movie_slug",
        "region_code",
        "region_name",
        "notify_attempts",
        "notify_last_error",
        "last_shows",
        "expired_at",
        "release_date",
    }
    assert expected <= set(Watch.__table__.columns.keys())
