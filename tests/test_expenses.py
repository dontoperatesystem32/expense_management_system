import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from main import app, get_session
from datetime import datetime, timezone, timedelta

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


def test_update_expense(client: TestClient):
    # Register and login user
    client.post("/users/register", json={"username": "user_update", "password": "pass_update"})
    login = client.post("/users/login", data={"username": "user_update", "password": "pass_update"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create an expense to update
    expense_data = {
        "amount": 25.0,
        "description": "Initial Description",
        "category": "Utilities"
    }
    create_response = client.post("/expenses", json=expense_data, headers=headers)
    assert create_response.status_code == 200
    created_expense = create_response.json()
    expense_id = created_expense["id"]

    # Update the expense
    updated_expense_data = {
        "amount": 30.0,
        "description": "Updated Description",
        "category": "Food"
    }
    update_response = client.put(f"/expenses/{expense_id}", json=updated_expense_data, headers=headers)
    assert update_response.status_code == 200
    updated_expense = update_response.json()
    assert updated_expense["id"] == expense_id
    assert updated_expense["amount"] == 30.0
    assert updated_expense["description"] == "Updated Description"
    assert updated_expense["category"] == "Food"

    # Verify the update by getting the expense
    get_response = client.get(f"/expenses/{expense_id}", headers=headers)
    assert get_response.status_code == 200
    fetched_expense = get_response.json()
    assert fetched_expense == updated_expense

def test_delete_expense(client: TestClient):
    # Register and login user
    client.post("/users/register", json={"username": "user_delete", "password": "pass_delete"})
    login = client.post("/users/login", data={"username": "user_delete", "password": "pass_delete"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create an expense to delete
    expense_data = {
        "amount": 15.0,
        "description": "To be deleted",
        "category": "Entertainment"
    }
    create_response = client.post("/expenses", json=expense_data, headers=headers)
    assert create_response.status_code == 200
    created_expense = create_response.json()
    expense_id = created_expense["id"]

    # Delete the expense
    delete_response = client.delete(f"/expenses/{expense_id}", headers=headers)
    assert delete_response.status_code == 200
    delete_message = delete_response.json()
    assert delete_message == {"message": "Expense deleted successfully"}

    # Verify deletion by trying to get the expense
    get_response = client.get(f"/expenses/{expense_id}", headers=headers)
    assert get_response.status_code == 404


def test_create_expense_invalid_amount(client: TestClient):
    # Register and login
    client.post("/users/register", json={"username": "user_delete", "password": "pass_delete"})
    login = client.post("/users/login", data={"username": "user_delete", "password": "pass_delete"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    invalid_expense_data = {
        "amount": -10.0,  # Invalid amount
        "description": "Invalid amount test",
        "category": "Testing"
    }
    response = client.post("/expenses", json=invalid_expense_data, headers=headers)
    assert response.status_code == 422  # Expect Unprocessable Entity
    assert "amount" in response.json()["detail"][0]["loc"] # Check error is related to 'amount'
    assert "greater_than" in response.json()["detail"][0]["type"] # Check for "greater_than_0" error type (or similar)


def test_create_expense_invalid_description_length(client: TestClient):
    # Register and login
    client.post("/users/register", json={"username": "user_desc_length", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_desc_length", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    invalid_expense_data = {
        "amount": 20.0,
        "description": "0", # Too short description
        "category": "Food"
    }
    response = client.post("/expenses", json=invalid_expense_data, headers=headers)
    assert response.status_code == 422
    assert "description" in response.json()["detail"][0]["loc"]
    assert "string_too_short" in response.json()["detail"][0]["type"]

    invalid_expense_data_long_desc = {
        "amount": 20.0,
        "description": "a" * 300, # Too long description
        "category": "Food"
    }
    response_long_desc = client.post("/expenses", json=invalid_expense_data_long_desc, headers=headers)
    assert response_long_desc.status_code == 422
    assert "description" in response_long_desc.json()["detail"][0]["loc"]
    assert "string_too_long" in response_long_desc.json()["detail"][0]["type"]


def test_create_expense_invalid_category_length(client: TestClient):
    # Register and login
    client.post("/users/register", json={"username": "user_cat_length", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_cat_length", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    invalid_expense_data = {
        "amount": 20.0,
        "description": "Valid description",
        "category": "Sh" # Too short category
    }
    response = client.post("/expenses", json=invalid_expense_data, headers=headers)
    assert response.status_code == 422
    assert "category" in response.json()["detail"][0]["loc"]
    assert "string_too_short" in response.json()["detail"][0]["type"]

    invalid_expense_data_long_cat = {
        "amount": 20.0,
        "description": "Valid description",
        "category": "a" * 150 # Too long category
    }
    response_long_cat = client.post("/expenses", json=invalid_expense_data_long_cat, headers=headers)
    assert response_long_cat.status_code == 422
    assert "category" in response_long_cat.json()["detail"][0]["loc"]
    assert "string_too_long" in response_long_cat.json()["detail"][0]["type"]

def test_update_expense_invalid_data(client: TestClient):
    # Register, login, create expense (setup)
    client.post("/users/register", json={"username": "user_update_invalid", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_update_invalid", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    expense_data = {"amount": 25.0, "description": "Initial", "category": "Test"}
    create_response = client.post("/expenses", json=expense_data, headers=headers)
    expense_id = create_response.json()["id"]

    updated_expense_data_invalid_amount = {
        "amount": "invalid", # Invalid amount type
        "description": "Updated Desc",
        "category": "Food"
    }
    update_response = client.put(f"/expenses/{expense_id}", json=updated_expense_data_invalid_amount, headers=headers)
    assert update_response.status_code == 422
    assert "amount" in update_response.json()["detail"][0]["loc"]
    assert "float_parsing" in update_response.json()["detail"][0]["type"]

# --- NON-EXISTENT RESOURCE TESTS ---
def test_get_nonexistent_expense(client: TestClient):
    # Register and login
    client.post("/users/register", json={"username": "user_nonexistent_get", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_nonexistent_get", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/expenses/9999", headers=headers) # Non-existent ID
    assert response.status_code == 404

def test_update_nonexistent_expense(client: TestClient):
    # Register and login
    client.post("/users/register", json={"username": "user_nonexistent_update", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_nonexistent_update", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    updated_expense_data = {
        "amount": 30.0,
        "description": "Updated Description",
        "category": "Food"
    }
    response = client.put("/expenses/9999", json=updated_expense_data, headers=headers) # Non-existent ID
    assert response.status_code == 404

def test_delete_nonexistent_expense(client: TestClient):
    # Register and login
    client.post("/users/register", json={"username": "user_nonexistent_delete", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_nonexistent_delete", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete("/expenses/9999", headers=headers) # Non-existent ID
    assert response.status_code == 404

# --- UNAUTHORIZED ACCESS TESTS ---
def test_update_expense_unauthorized(client: TestClient):
    # Create two users
    client.post("/users/register", json={"username": "user1_auth_update", "password": "pass1"})
    client.post("/users/register", json={"username": "user2_auth_update", "password": "pass2"})
    token1 = client.post("/users/login", data={"username": "user1_auth_update", "password": "pass1"}).json()["access_token"]
    token2 = client.post("/users/login", data={"username": "user2_auth_update", "password": "pass2"}).json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User 1 creates expense
    expense_data = {"amount": 25.0, "description": "User1 Expense", "category": "Test"}
    create_response = client.post("/expenses", json=expense_data, headers=headers1)
    expense_id = create_response.json()["id"]

    # User 2 tries to update User 1's expense
    updated_expense_data = {"amount": 30.0, "description": "User2 Update Attempt", "category": "Food"}
    update_response = client.put(f"/expenses/{expense_id}", json=updated_expense_data, headers=headers2)
    assert update_response.status_code == 404 # Or 403, depending on desired security

def test_delete_expense_unauthorized(client: TestClient):
    # Create two users
    client.post("/users/register", json={"username": "user1_auth_delete", "password": "pass1"})
    client.post("/users/register", json={"username": "user2_auth_delete", "password": "pass2"})
    token1 = client.post("/users/login", data={"username": "user1_auth_delete", "password": "pass1"}).json()["access_token"]
    token2 = client.post("/users/login", data={"username": "user2_auth_delete", "password": "pass2"}).json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}
    headers2 = {"Authorization": f"Bearer {token2}"}

    # User 1 creates expense
    expense_data = {"amount": 25.0, "description": "User1 Expense", "category": "Test"}
    create_response = client.post("/expenses", json=expense_data, headers=headers1)
    expense_id = create_response.json()["id"]

    # User 2 tries to delete User 1's expense
    delete_response = client.delete(f"/expenses/{expense_id}", headers=headers2)
    assert delete_response.status_code == 404 # Or 403

# --- NO TOKEN ACCESS TESTS ---
def test_create_expense_no_token(client: TestClient):
    expense_data = {"amount": 25.0, "description": "No Token Expense", "category": "Test"}
    response = client.post("/expenses", json=expense_data)
    assert response.status_code == 401

def test_get_expenses_no_token(client: TestClient):
    response = client.get("/expenses")
    assert response.status_code == 401

def test_get_expense_by_id_no_token(client: TestClient):
    response = client.get("/expenses/1")
    assert response.status_code == 401

def test_update_expense_no_token(client: TestClient):
    updated_expense_data = {"amount": 30.0, "description": "No Token Update", "category": "Food"}
    response = client.put("/expenses/1", json=updated_expense_data)
    assert response.status_code == 401

def test_delete_expense_no_token(client: TestClient):
    response = client.delete("/expenses/1")
    assert response.status_code == 401

# --- FILTERING AND PAGINATION EDGE CASES ---
def test_expense_date_filter_no_match(client: TestClient):
    # Register, login, create expense (setup)
    client.post("/users/register", json={"username": "user_date_filter_no_match", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_date_filter_no_match", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    expense_data = {"amount": 25.0, "description": "Date Filter Test", "category": "Test", "date": "2024-01-01T10:00:00Z"}
    client.post("/expenses", json=expense_data, headers=headers)

    response = client.get("/expenses?start_date=2025-01-01&end_date=2025-01-31", headers=headers)
    assert response.status_code == 200
    assert response.json() == [] # Expect empty list

def test_expense_category_filter_no_match(client: TestClient):
    # Register, login, create expense (setup)
    client.post("/users/register", json={"username": "user_cat_filter_no_match", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_cat_filter_no_match", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    expense_data = {"amount": 25.0, "description": "Category Filter Test", "category": "Food"}
    client.post("/expenses", json=expense_data, headers=headers)

    response = client.get("/expenses?category=NonExistentCategory", headers=headers)
    assert response.status_code == 200
    assert response.json() == [] # Expect empty list

def test_expense_pagination_zero_limit(client: TestClient):
    # Register, login, create expense (setup - create a few expenses if needed for pagination to be meaningful)
    client.post("/users/register", json={"username": "user_page_zero_limit", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_page_zero_limit", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(3): # Create a few expenses
        expense_data = {"amount": 25.0 + i * 5, "description": f"Pagination Test {i}", "category": "Test"}
        client.post("/expenses", json=expense_data, headers=headers)

    response = client.get("/expenses?limit=0", headers=headers)
    assert response.status_code == 200
    assert response.json() == [] # Expect empty list or handle gracefully - empty list is fine

def test_expense_pagination_skip_too_high(client: TestClient):
    # Register, login, create expense (setup - create a few expenses)
    client.post("/users/register", json={"username": "user_page_skip_high", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_page_skip_high", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    for i in range(2): # Create 2 expenses
        expense_data = {"amount": 25.0 + i * 5, "description": f"Pagination Skip Test {i}", "category": "Test"}
        client.post("/expenses", json=expense_data, headers=headers)

    response = client.get("/expenses?skip=5&limit=2", headers=headers) # Skip more than available
    assert response.status_code == 200
    assert response.json() == [] # Expect empty list

def test_expense_filters_and_pagination(client: TestClient):
    # Register, login, create expenses with varying dates and categories
    client.post("/users/register", json={"username": "user_filters_page", "password": "pass"})
    token = client.post("/users/login", data={"username": "user_filters_page", "password": "pass"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    expenses = [
        {"amount": 10, "description": "Expense 1", "category": "Food", "date": "2025-01-05T10:00:00Z"},
        {"amount": 20, "description": "Expense 2", "category": "Transport", "date": "2025-01-15T10:00:00Z"},
        {"amount": 30, "description": "Expense 3", "category": "Food", "date": "2025-01-25T10:00:00Z"},
        {"amount": 40, "description": "Expense 4", "category": "Entertainment", "date": "2025-02-05T10:00:00Z"},
    ]
    for exp in expenses:
        client.post("/expenses", json=exp, headers=headers)

    # Filter by category=Food, date range 2025-01-01 to 2025-01-31, limit=2, skip=1
    response = client.get("/expenses?category=Food&start_date=2025-01-01&end_date=2025-01-31&limit=1&skip=1", headers=headers)
    assert response.status_code == 200
    filtered_expenses = response.json()
    assert len(filtered_expenses) == 1
    assert filtered_expenses[0]["description"] == "Expense 3" # Expecting the second "Food" expense due to skip=1

# --- DATA TYPE VALIDATION TESTS ---
def test_expense_invalid_date_format_filter(client: TestClient):
    # Register and login
    client.post("/users/register", json={"username": "user_invalid_date_format", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_invalid_date_format", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.get("/expenses?start_date=01-01-2025", headers=headers) # Invalid date format MM-DD-YYYY
    assert response.status_code == 422 # Expect 422 for invalid date format
    assert "datetime_parsing" in response.json()["detail"][0]["type"]

# --- DEFAULT VALUE TESTS ---
def test_update_expense_last_updated_field(client: TestClient):
    # Register, login, create expense (setup)
    client.post("/users/register", json={"username": "user_last_updated", "password": "pass"})
    login = client.post("/users/login", data={"username": "user_last_updated", "password": "pass"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    expense_data = {"amount": 25.0, "description": "Last Updated Test", "category": "Test"}
    create_response = client.post("/expenses", json=expense_data, headers=headers)
    expense_id = create_response.json()["id"]

    get_response_before_update = client.get(f"/expenses/{expense_id}", headers=headers)
    expense_before_update = get_response_before_update.json()
    last_updated_before = datetime.fromisoformat(expense_before_update["last_updated"].replace("Z", "+00:00"))

    # Update expense
    updated_expense_data = {"amount": 30.0, "description": "Updated Description", "category": "Food"}
    update_response = client.put(f"/expenses/{expense_id}", json=updated_expense_data, headers=headers)
    assert update_response.status_code == 200

    get_response_after_update = client.get(f"/expenses/{expense_id}", headers=headers)
    expense_after_update = get_response_after_update.json()
    last_updated_after = datetime.fromisoformat(expense_after_update["last_updated"].replace("Z", "+00:00"))

    assert last_updated_after > last_updated_before # last_updated should be newer after update
