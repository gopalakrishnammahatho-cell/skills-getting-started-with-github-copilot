import os
os.environ["TESTING"] = "1"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from src.app import app
from src.database import get_db, engine
from src.models import Base, Activity, Participant

# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Use the same engine as the app
test_engine = engine

# Create test session factory
TestingSessionLocal = sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

# Override the dependency
app.dependency_overrides[get_db] = override_get_db

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
async def db_session():
    # Create tables for test engine
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Also create for app engine to ensure
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        await session.close()

    # Drop tables after test
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture(scope="function")
async def client(db_session):
    # TestClient can handle async apps
    with TestClient(app) as c:
        yield c

@pytest.mark.asyncio
async def test_get_activities(client, db_session):
    # Arrange
    activities_data = [
        {"name": "Chess Club", "description": "Learn strategies", "schedule": "Fridays", "max_participants": 12},
        {"name": "Programming Class", "description": "Learn programming", "schedule": "Tuesdays", "max_participants": 20},
    ]
    for data in activities_data:
        activity = Activity(**data)
        db_session.add(activity)
    await db_session.commit()

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "Chess Club" in data
    assert "Programming Class" in data
    assert data["Chess Club"]["description"] == "Learn strategies"

@pytest.mark.asyncio
async def test_signup_for_activity_success(client, db_session):
    # Arrange
    activity = Activity(name="Chess Club", description="Learn strategies", schedule="Fridays", max_participants=12)
    db_session.add(activity)
    await db_session.commit()

    # Act
    response = client.post("/activities/Chess Club/signup", params={"email": "test@example.com"})

    # Assert
    assert response.status_code == 200
    assert "Signed up test@example.com for Chess Club" in response.json()["message"]

@pytest.mark.asyncio
async def test_signup_for_nonexistent_activity(client):
    # Arrange
    # No setup needed - activity doesn't exist

    # Act
    response = client.post("/activities/Nonexistent/signup", params={"email": "test@example.com"})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"

@pytest.mark.asyncio
async def test_signup_already_signed_up(client, db_session):
    # Arrange
    activity = Activity(name="Chess Club", description="Learn strategies", schedule="Fridays", max_participants=12)
    db_session.add(activity)
    await db_session.commit()

    # First signup
    client.post("/activities/Chess Club/signup", params={"email": "test@example.com"})

    # Act
    response = client.post("/activities/Chess Club/signup", params={"email": "test@example.com"})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"

@pytest.mark.asyncio
async def test_unregister_from_activity_success(client, db_session):
    # Arrange
    activity = Activity(name="Chess Club", description="Learn strategies", schedule="Fridays", max_participants=12)
    db_session.add(activity)
    await db_session.commit()

    # Signup first
    client.post("/activities/Chess Club/signup", params={"email": "test@example.com"})

    # Act
    response = client.delete("/activities/Chess Club/signup", params={"email": "test@example.com"})

    # Assert
    assert response.status_code == 200
    assert "Unregistered test@example.com from Chess Club" in response.json()["message"]

@pytest.mark.asyncio
async def test_unregister_from_nonexistent_activity(client):
    # Arrange
    # No setup needed - activity doesn't exist

    # Act
    response = client.delete("/activities/Nonexistent/signup", params={"email": "test@example.com"})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"

@pytest.mark.asyncio
async def test_unregister_not_signed_up(client, db_session):
    # Arrange
    activity = Activity(name="Chess Club", description="Learn strategies", schedule="Fridays", max_participants=12)
    db_session.add(activity)
    await db_session.commit()

    # Act
    response = client.delete("/activities/Chess Club/signup", params={"email": "notsigned@example.com"})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student not signed up for this activity"