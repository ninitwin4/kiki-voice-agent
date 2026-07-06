import os

# Must be set before backend.main imports backend.config.
os.environ["MOCK_DELAY_SECONDS"] = "0"
os.environ["MOCK_MODE"] = "true"
os.environ["PAYMENT_MOCK"] = "true"

import pytest
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        c.post("/demo/reset")
        yield c
