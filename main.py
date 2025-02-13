from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from typing import Annotated, Optional
from datetime import datetime, timedelta, timezone
import jwt
from jwt.exceptions import InvalidTokenError
from sqlmodel import Session, select
from passlib.context import CryptContext
from models import User, UserCreate, UserRead, Expense, ExpenseCreate, ExpenseRead, Token, TokenData
from sqlmodel import SQLModel, create_engine

# Database setup
sqlite_url = "sqlite:///database.db"
engine = create_engine(sqlite_url, echo=True)  # echo=True for debugging

# Lifespan event handler
@asynccontextmanager
async def lifespan(app: FastAPI):
    #create database tables on startup
    SQLModel.metadata.create_all(engine)
    yield
    # Cleanup on shutdown (if needed)
    # engine.dispose()  # Optional: Close database connections

# FastAPI app with lifespan
app = FastAPI(lifespan=lifespan)

# Security setup
SECRET_KEY = "your-secret-key-here"
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
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Session = Depends(get_session)
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
    current_user: Annotated[User, Depends(get_current_user)]
):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

# Authentication endpoints
@app.post("/users/login", response_model=Token)
async def login_for_access_token(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    session: Session = Depends(get_session)
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
async def create_user(
    user: UserCreate,
    session: Session = Depends(get_session)
):
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
    current_user: Annotated[User, Depends(get_current_active_user)]
):
    return current_user

# Expense endpoints
@app.post("/expenses", response_model=ExpenseRead)
async def create_expense(
    expense: ExpenseCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session)
):
    db_expense = Expense(**expense.model_dump(), owner_id=current_user.id)
    
    session.add(db_expense)
    session.commit()
    session.refresh(db_expense)
    
    return db_expense

@app.get("/expenses", response_model=list[ExpenseRead])
async def get_expenses(
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session)
):
    statement = select(Expense).where(Expense.owner_id == current_user.id)
    expenses = session.exec(statement).all()
    return expenses

@app.get("/expenses/{expense_id}", response_model=ExpenseRead)
async def get_expense(
    expense_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session)
    
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
    session: Session = Depends(get_session)
):
    db_expense = session.get(Expense, expense_id)
    if not db_expense or db_expense.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    for key, value in expense_data.model_dump().items():
        setattr(db_expense, key, value)
    
    db_expense.last_updated = datetime.now(timezone.utc)
    
    session.add(db_expense)
    session.commit()
    session.refresh(db_expense)
    
    return db_expense

@app.delete("/expenses/{expense_id}")
async def delete_expense(
    expense_id: int,
    current_user: Annotated[User, Depends(get_current_active_user)],
    session: Session = Depends(get_session)
):
    expense = session.get(Expense, expense_id)
    if not expense or expense.owner_id != current_user.id:
        raise HTTPException(status_code=404, detail="Expense not found")
    
    session.delete(expense)
    session.commit()
    
    return {"message": "Expense deleted successfully"}