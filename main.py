from fastapi import FastAPI
from fastapi import FastAPI, HTTPException
from models import Expense, expenses_db
from datetime import datetime, timezone

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello, FastAPI!"}

@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    return {"item_id": item_id, "query": q}


#create an expense
@app.post("/expenses", response_model=Expense)
def create_expense(expense: Expense):
    # Add expense to the in-memory database
    expenses_db.append(expense)
    return expense


#list all expenses
@app.get("/expenses", response_model=list[Expense])
def get_expenses():
    return expenses_db


# Retrieve a specific expense by ID
@app.get("/expenses/{expense_id}", response_model=Expense)
def get_expense_by_id(expense_id: str):
    for expense in expenses_db:
        if expense.id == expense_id:
            return expense
    raise HTTPException(status_code=404, detail="Expense not found")


@app.put("/expenses/{expense_id}", response_model=Expense)
def update_expense(expense_id: str, updated_expense: Expense):
    for index, expense in enumerate(expenses_db):
        if expense.id == expense_id:
            # Preserve original date, update only necessary fields
            updated_expense.id = expense_id
            updated_expense.date = expense.date
            updated_expense.last_updated = datetime.now(timezone.utc).isoformat()  # Update timestamp
            
            # Replace the old record
            expenses_db[index] = updated_expense
            return updated_expense
    
    raise HTTPException(status_code=404, detail="Expense not found")
    


# DELETE an expense by ID
@app.delete("/expenses/{expense_id}", response_model=dict)
def delete_expense(expense_id: str):
    for index, expense in enumerate(expenses_db):
        if expense.id == expense_id:
            del expenses_db[index]  # Remove expense from the list
            return {"message": "Expense deleted successfully"}
    
    raise HTTPException(status_code=404, detail="Expense not found")

