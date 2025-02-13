import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from main import app, get_session

def test_register_user(client: TestClient):
    # Test successful registration
    response = client.post("/users/register", json={
        "username": "testuser",
        "password": "testpass"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert "id" in data
    assert "hashed_password" not in data

    # Test duplicate registration
    response = client.post("/users/register", json={
        "username": "testuser",
        "password": "testpass"
    })
    assert response.status_code == 400
    assert "Username already registered" in response.json()["detail"]

def test_login_user(client: TestClient):
    # Register first
    client.post("/users/register", json={
        "username": "testuser",
        "password": "testpass"
    })
    
    # Test valid login
    response = client.post("/users/login", data={
        "username": "testuser",
        "password": "testpass"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Test invalid login
    response = client.post("/users/login", data={
        "username": "testuser",
        "password": "wrongpass"
    })
    assert response.status_code == 401