from datetime import date, timedelta, UTC

import datetime
import os
from contextlib import asynccontextmanager
from typing import Annotated, List, Optional

import jwt
from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jwt.exceptions import InvalidTokenError
from passlib.context import CryptContext
from sqlmodel import Session, SQLModel, create_engine, select

from models import (Expense, ExpenseCreate, ExpenseRead, Token, TokenData, CategoryBase, CategoryCreate, CategoryRead, Category,
                    User, UserCreate, UserRead)

# Database setup
sqlite_url = "sqlite:///database.db"
engine = create_engine(sqlite_url, echo=True)  # echo=True for debugging


# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    # create database tables on startup
    SQLModel.metadata.create_all(engine)
    yield
    # Cleanup on shutdown (if needed)
    # engine.dispose()  # Optional: Close database connections


# FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Security setup
SECRET_KEY = os.environ.get("SECRET_KEY")
if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable not set!")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/login")


# Database dependency
def get_session():
    with Session(engine) as session:
        yield session


# Authentication functions
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str):
    return pwd_context.hash(password)


def get_user(session: Session, username: str) -> Optional[User]:
    statement = select(User).where(User.username == username)
    return session.exec(statement).first()


def authenticate_user(session: Session, username: str, password: str):
    user = get_user(session, username)
    if not user or not verify_password(password, user.hashed_password):
        return False
    return user


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.datetime.now(UTC) + expires_delta
    else:
        expire = datetime.datetime.now(UTC) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Session = Depends(get_session),
):
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

    user = get_user(session, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)],
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# Authentication endpoints
@app.post("/users/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session),
):
    user = authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@app.post("/users/register", response_model=UserRead)
async def create_user(user: UserCreate, session: Session = Depends(get_session)):
    existing_user = get_user(session, user.username)
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already registered")

    hashed_password = get_password_hash(user.password)
    db_user = User(username=user.username, hashed_password=hashed_password)

    session.add(db_user)
    session.commit()
    session.refresh(db_user)

    return db_user


@app.get("/users/me", response_model=UserRead)
async def read_users_me(
    current_user: Annotated[User, Depends(get_current_active_user)],
):
    return current_user


# Expense endpoints
@app.post("/expenses", response_model=ExpenseRead)
async def create_expense(
    expense: ExpenseCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    db_expense = Expense(**expense.model_dump(), owner_id=current_user.id)

    session.add(db_expense)
    session.commit()
    session.refresh(db_expense)

    return db_expense


@app.get("/expenses", response_model=List[ExpenseRead])
async def get_expenses(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
    start_date: Optional[date] = Query(
        None, description="Filter expenses created on or after this date (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="Filter expenses created on or before this date (YYYY-MM-DD)"
    ),
    category: Optional[str] = Query(None, description="Filter expenses by category"),
    skip: int = Query(0, description="Number of records to skip for pagination", ge=0),
    limit: int = Query(100, description="Maximum number of records to return", le=1000),
):
    # base query
    query = select(Expense).where(Expense.owner_id == current_user.id)

    # Apply date range filter
    if start_date:
        query = query.where(Expense.date >= start_date)
    if end_date:
        query = query.where(Expense.date <= end_date)

    # Apply category filter
    if category:
        query = query.where(Expense.category == category)

    # Apply pagination
    query = query.offset(skip).limit(limit)

    expenses = session.exec(query).all()
    return expenses


@app.get("/expenses/{expense_id}", response_model=ExpenseRead)
async def get_expense(
    expense_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    expense = session.get(Expense, expense_id)
    if not expense or expense.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Expense not found")
    return expense


@app.put("/expenses/{expense_id}", response_model=ExpenseRead)
async def update_expense(
    expense_id: int,
    expense_data: ExpenseCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    db_expense = session.get(Expense, expense_id)
    if not db_expense or db_expense.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Expense not found")

    for key, value in expense_data.model_dump().items():
        setattr(db_expense, key, value)

    db_expense.last_updated = datetime.datetime.now(UTC)

    session.add(db_expense)
    session.commit()
    session.refresh(db_expense)

    return db_expense


@app.delete("/expenses/{expense_id}")
async def delete_expense(
    expense_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    expense = session.get(Expense, expense_id)
    if not expense or expense.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Expense not found")

    session.delete(expense)
    session.commit()

    return {"message": "Expense deleted successfully"}



@app.post("/categories", response_model=CategoryRead)
async def create_category(
    category: CategoryCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
):
    db_category = Category(**category.model_dump())

    session.add(db_category)
    session.commit()
    session.refresh(db_category)

    return db_category



@app.get("/categories", response_model=List[CategoryRead])
async def get_categories(
    session: Session = Depends(get_session),
    skip: int = Query(0, description="Pagination offset"),
    limit: int = Query(100, description="Maximum results per page", le=1000)
):
    """
    Retrieve all categories with optional pagination.
    """
    query = select(Category).offset(skip).limit(limit)
    categories = session.exec(query).all()
    return categories


@app.get("/categories/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: int,
    session: Session = Depends(get_session)
):
    """
    Retrieve a specific category by its ID.
    """
    category = session.get(Category, category_id)
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    return category




#stage 3



@app.get("/reports/expenses", response_model=dict)
async def get_expenses_report(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session),
    start_date: Optional[date] = Query(
        None, description="Filter expenses created on or after this date (YYYY-MM-DD)"
    ),
    end_date: Optional[date] = Query(
        None, description="Filter expenses created on or before this date (YYYY-MM-DD)"
    )
):
    # base query
    query = select(Expense).where(Expense.owner_id == current_user.id)

    # Apply date range filter
    if start_date:
        query = query.where(Expense.date >= start_date)
    if end_date:
        query = query.where(Expense.date <= end_date)

    report_dict = dict()

    expenses = session.exec(query).all()

    #get number of categories

    categories = []
    # categories_number = 0

    for expense in expenses:
        categories.append(expense.category_id)

    categories = set(categories)
    print("\ncategories number: ", len(categories))

    # categories_amount = len(categories)
    
    #iterate over categories
    for category_id in categories:
        temp_query = query.where(Expense.category_id == category_id)
        expenses_per_cat = session.exec(temp_query).all()
        category_sum = 0
        for expense in expenses_per_cat:
            category_sum = category_sum + expense.amount
        print(f'category id: {category_id} category_sum = {category_sum}')
        report_dict[str(category_id)] = category_sum

    print(f'report: \n {report_dict}')

    return report_dict


    
