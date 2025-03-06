import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from src.main import app, get_db  # Assuming you're using SQLAlchemy
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from src.utils.init_database import init_database



client = TestClient(app)

@pytest.fixture(scope="function")  # Makes sure every test has its own database session
def db_session(db_session):
    yield db_session
    db_session.rollback()  # Important for cleaning up after each test

def test_create_player_success(db_session):
    response = client.post("/create_player/", json={"player_name": "TestUser"})
    assert response.status_code == 200
    data = response.json()
    assert "player_id" in data
    assert "username" in data
    assert data["username"] == "TestUser"

    # Verify the database change
    player = db_session.execute(text("SELECT * FROM player_progress WHERE username = 'TestUser'")).fetchone()
    assert player is not None


def test_create_player_existing_username(db_session):
    client.post("/create_player/", json={"player_name": "ExistingUser"})
    response = client.post("/create_player/", json={"player_name": "ExistingUser"})
    assert response.status_code == 400 # Change status code here.


def test_create_player_invalid_username(db_session):
    response = client.post("/create_player/", json={"player_name": ""})
    assert response.status_code == 422 # assuming you have input validation


def test_create_player_invalid_json(db_session):
    response = client.post("/create_player/", json={"invalid": "json"})
    assert response.status_code == 422 # assuming you have proper error handling
