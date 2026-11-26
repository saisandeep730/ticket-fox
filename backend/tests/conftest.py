import os
import tempfile
import pytest

# Point every test at a throwaway database so a local dev DB is never touched.
TEST_DB_PATH = os.path.join(tempfile.gettempdir(), "ticketfox_pytest_isolated.db").replace("\\", "/")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{TEST_DB_PATH}"
os.environ["ALLOW_MOCK_AUTH"] = "true"

@pytest.fixture(scope="session", autouse=True)
def isolated_test_db():
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
    yield
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except Exception:
            pass
