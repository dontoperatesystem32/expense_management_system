from fastapi.testclient import TestClient
from main import app
from models import Expense
import uuid
import pytest

client = TestClient(app)

# Sample expense data
def get_sample_expense():
    return {
        "id": str(uuid.uuid4()),
        "amount": 50.75,
        "description": "Lunch",
        "category": "Food"
    }

# Test root endpoint
def test_read_root():
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello, FastAPI!"}

# Test listing expenses (initially empty)
def test_get_expenses_empty():
    response = client.get("/expenses")
    assert response.status_code == 200
    assert response.json() == []

# Test creating an expense
def test_create_expense():
    expense_data = get_sample_expense()
    response = client.post("/expenses", json=expense_data)
    assert response.status_code == 200
    assert response.json()["amount"] == expense_data["amount"]
    assert response.json()["description"] == expense_data["description"]
    assert response.json()["category"] == expense_data["category"]

# Test getting all expenses (after adding one)
def test_get_expenses_non_empty():
    response = client.get("/expenses")
    assert response.status_code == 200
    assert len(response.json()) > 0  # Ensure at least one expense exists

# Test retrieving an expense by ID
def test_get_expense_by_id():
    # Create a sample expense
    expense_data = get_sample_expense()
    post_response = client.post("/expenses", json=expense_data)
    expense_id = post_response.json()["id"]

    # Retrieve it by ID
    response = client.get(f"/expenses/{expense_id}")
    assert response.status_code == 200
    assert response.json()["id"] == expense_id

# Test updating an expense
def test_update_expense():
    # Create a sample expense
    expense_data = get_sample_expense()
    post_response = client.post("/expenses", json=expense_data)
    expense_id = post_response.json()["id"]

    # Updated expense data
    updated_expense = expense_data.copy()
    updated_expense["amount"] = 75.99
    updated_expense["description"] = "Dinner"

    # Send PUT request
    response = client.put(f"/expenses/{expense_id}", json=updated_expense)
    assert response.status_code == 200
    assert response.json()["amount"] == 75.99
    assert response.json()["description"] == "Dinner"

# Test deleting an expense
def test_delete_expense():
    # Create a sample expense
    expense_data = get_sample_expense()
    post_response = client.post("/expenses", json=expense_data)
    expense_id = post_response.json()["id"]

    # Delete the expense
    response = client.delete(f"/expenses/{expense_id}")
    assert response.status_code == 200
    assert response.json() == {"message": "Expense deleted successfully"}

    # Verify deletion
    response = client.get(f"/expenses/{expense_id}")
    assert response.status_code == 404
