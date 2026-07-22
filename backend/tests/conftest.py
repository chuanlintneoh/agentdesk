import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    # Yields a FastAPI test client instance for testing routing
    with TestClient(app) as c:
        yield c
