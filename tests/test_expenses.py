import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from main import app, get_session
from time import sleep

def test_create_and_get_expenses(client):
    # Register and login
    client.post("/users/register", json={"username": "user1", "password": "pass1"})
    login = client.post("/users/login", data={"username": "user1", "password": "pass1"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create expense
    expense_data = {
        "amount": 50.0,
        "description": "Groceries",
        "category": "Food"
    }
    response = client.post("/expenses", json=expense_data, headers=headers)
    assert response.status_code == 200
    created_expense = response.json()
    assert created_expense["amount"] == 50.0
    assert created_expense["owner_id"] == 1  # First user

    # Get expenses
    response = client.get("/expenses", headers=headers)
    assert response.status_code == 200
    expenses = response.json()
    assert len(expenses) == 1
    assert expenses[0]["id"] == 1
    
def test_expense_security(client: TestClient):
    # Create two users
    client.post("/users/register", json={"username": "user1", "password": "pass1"})
    client.post("/users/register", json={"username": "user2", "password": "pass2"})
    
    # Get their tokens
    token1 = client.post("/users/login", data={"username": "user1", "password": "pass1"}).json()["access_token"]
    token2 = client.post("/users/login", data={"username": "user2", "password": "pass2"}).json()["access_token"]
    
    # User1 creates expense
    client.post("/expenses", json={
        "amount": 100,
        "description": "Test",
        "category": "Test"
    }, headers={"Authorization": f"Bearer {token1}"})
    
    # User2 tries to access it
    response = client.get("/expenses/1", headers={"Authorization": f"Bearer {token2}"})
    assert response.status_code == 404

def test_expense_filters(client: TestClient):
    # Setup user and expenses
    client.post("/users/register", json={"username": "user", "password": "pass"})
    token = client.post("/users/login", data={"username": "user", "password": "pass"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    # Create multiple expenses
    expenses = [
        {"amount": 10, "description": "Adsaefsaedfsaf", "category": "Food", "date": "2025-01-01T17:17:20.044Z"},
        {"amount": 20, "description": "Badadadada", "category": "Food", "date": "2025-01-30T17:17:20.044Z"},
        {"amount": 30, "description": "Cadadadadad", "category": "Transport", "date": "2025-02-13T17:17:20.044Z"}
    ]
    for exp in expenses:
        response = client.post("/expenses", json=exp, headers=headers)
        assert response.status_code ==200
    # Test date filter
    response = client.get("/expenses?start_date=2025-01-01&end_date=2025-01-31", headers=headers)
    assert len(response.json()) == 2
    
    # Test category filter
    response = client.get("/expenses?category=Transport", headers=headers)
    assert len(response.json()) == 1
    assert response.json()[0]["amount"] == 30
    
    # Test pagination
    response = client.get("/expenses?skip=1&limit=2", headers=headers)
    assert len(response.json()) == 2