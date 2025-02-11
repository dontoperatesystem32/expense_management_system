from fastapi import Depends, FastAPI, HTTPException, status
from models import Expense, expenses_db, User, UserInDB, UserDTO, users_db, Token, TokenData
from datetime import datetime, timezone, timedelta
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated
from passlib.context import CryptContext
import jwt
from jwt.exceptions import InvalidTokenError


app = FastAPI()

SECRET_KEY = "09d25e094faa6ca2556c818166b7a9563b93f7099f6f0f4caa6cf63b88e8d3e7"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")



def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password):
    return pwd_context.hash(password)


def authenticate_user(users_db, username: str, password: str):
    user = get_user(users_db, username)
    if not user:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_user(users_db, username: str):
    for user in users_db:
        if user.username == username:
            return user
    return None


async def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except InvalidTokenError:
        raise credentials_exception
    user = get_user(users_db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# @app.post("/token")
@app.post("/users/login")
async def login_for_access_token(form_data: Annotated[OAuth2PasswordRequestForm, Depends()]) -> Token:
    user = authenticate_user(users_db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return Token(access_token=access_token, token_type="bearer")

@app.get("/users/me")
async def read_users_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user


@app.post("/users/register", response_model=User)
async def create_user(user: UserDTO):
    # Check if the username already exists
    if user.username in users_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    # Hash the user's password before storing it
    hashed_password = get_password_hash(user.password)
    
    # Create a new User instance with the hashed password
    user_in_db = User(**user.model_dump(), disabled = False, hashed_password=hashed_password)
    
    # Store the user in the database (here we're using the in-memory users_db dictionary)
    users_db.append(user_in_db)

    print("users_db: \n" + str(users_db))
    
    # Return the created user
    return user_in_db




#stage 1

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

