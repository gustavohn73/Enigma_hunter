import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text, create_engine
from sqlalchemy.orm import sessionmaker
from src.main import app, get_db, SessionLocal  # Import SessionLocal
from sqlalchemy.exc import IntegrityError
from src.utils.init_database import init_database
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Configurações para o pytest
client = TestClient(app)

@pytest.fixture(scope="function")
def db_session():
    """Cria e limpa uma sessão de banco de dados para cada teste"""
    engine = create_engine("sqlite:///:memory:")  # Use in-memory database for testing
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    logger.info("Starting new database session for test.")
    try:
        yield db
    finally:
        logger.info("Rolling back database session.")
        db.rollback()
        db.close()
        engine.dispose()
        logger.info("Database session closed.")


def test_create_player_success(db_session):
    logger.info("Starting test_create_player_success")
    response = client.post("/create_player/", json={"player_name": "TestUser"})
    logger.info(f"Response status code: {response.status_code}")
    logger.info(f"Response JSON: {response.json()}")
    assert response.status_code == 200
    data = response.json()
    assert "player_id" in data
    assert "username" in data
    assert data["username"] == "TestUser"

    # Verify the database change
    player = db_session.execute(text("SELECT * FROM player_progress WHERE username = 'TestUser'")).fetchone()
    logger.info(f"Database query result: {player}")
    assert player is not None
    logger.info("test_create_player_success finished successfully.")


def test_create_player_existing_username(db_session):
    logger.info("Starting test_create_player_existing_username")
    client.post("/create_player/", json={"player_name": "ExistingUser"})
    response = client.post("/create_player/", json={"player_name": "ExistingUser"})
    logger.info(f"Response status code: {response.status_code}")
    assert response.status_code == 400


def test_create_player_invalid_username(db_session):
    logger.info("Starting test_create_player_invalid_username")
    response = client.post("/create_player/", json={"player_name": ""})
    logger.info(f"Response status code: {response.status_code}")
    assert response.status_code == 422


def test_create_player_invalid_json(db_session):
    logger.info("Starting test_create_player_invalid_json")
    response = client.post("/create_player/", json={"invalid": "json"})
    logger.info(f"Response status code: {response.status_code}")
    assert response.status_code == 422
