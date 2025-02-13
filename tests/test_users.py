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

    # Test missing username
    response = client.post("/users/register", json={
        "password": "testpass"
    })
    assert response.status_code == 422 # Unprocessable Entity
    assert "username" in response.json()["detail"][0]["loc"]
    assert "missing" in response.json()["detail"][0]["type"]

    # Test missing password
    response = client.post("/users/register", json={
        "username": "testuser"
    })
    assert response.status_code == 422 # Unprocessable Entity
    assert "password" in response.json()["detail"][0]["loc"]
    assert "missing" in response.json()["detail"][0]["type"]


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

    # Test invalid login - wrong password
    response = client.post("/users/login", data={
        "username": "testuser",
        "password": "wrongpass"
    })
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

    # Test invalid login - wrong username
    response = client.post("/users/login", data={
        "username": "wronguser",
        "password": "testpass"
    })
    assert response.status_code == 401
    assert "Incorrect username or password" in response.json()["detail"]

    # Test missing username for login
    response = client.post("/users/login", data={
        "password": "testpass"
    })
    assert response.status_code == 422 # Unprocessable Entity
    assert "username" in response.json()["detail"][0]["loc"]
    assert "missing" in response.json()["detail"][0]["type"]

    # Test missing password for login
    response = client.post("/users/login", data={
        "username": "testuser"
    })
    assert response.status_code == 422 # Unprocessable Entity
    assert "password" in response.json()["detail"][0]["loc"]
    assert "missing" in response.json()["detail"][0]["type"]

def test_read_users_me(client: TestClient):
    # Register and login user
    client.post("/users/register", json={"username": "me_user", "password": "me_pass"})
    login = client.post("/users/login", data={"username": "me_user", "password": "me_pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Test get current user successfully
    response = client.get("/users/me", headers=headers)
    assert response.status_code == 200
    me_data = response.json()
    assert me_data["username"] == "me_user"
    assert "id" in me_data

    # Test no token access
    response_no_token = client.get("/users/me")
    assert response_no_token.status_code == 401

    # Test invalid token (you'd ideally test with an expired or malformed token, but for simplicity, an empty string is sufficient to represent invalid token for this test)
    headers_invalid_token = {"Authorization": "Bearer invalid_token"} # In real app, test with jwt.ExpiredSignatureError etc.
    response_invalid_token = client.get("/users/me", headers=headers_invalid_token)
    assert response_invalid_token.status_code == 401
