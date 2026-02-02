from app.db.session import _to_async_dsn


def test_to_async_dsn_converts_psycopg_to_asyncpg():
    assert _to_async_dsn("postgresql+psycopg://u:p@h/db").startswith("postgresql+asyncpg://")


def test_to_async_dsn_no_change_for_other_schemes():
    assert _to_async_dsn("sqlite+aiosqlite:///x.db").startswith("sqlite+aiosqlite:///")

