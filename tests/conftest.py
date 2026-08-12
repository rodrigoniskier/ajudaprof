import io
import re

import pytest

from app import create_app
from app.config import TestConfig


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    yield app


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def csrf(client):
    response = client.get("/")
    match = re.search(rb'name="csrf_token" value="([^"]+)"', response.data)
    assert match
    return match.group(1).decode("utf-8")


def upload(name="fonte.txt", text="Documento acadêmico de referência."):
    return io.BytesIO(text.encode("utf-8")), name

