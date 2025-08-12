# app/routes/auth.py
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserLogin, UserResponse, Token, StandardResponse
from app.core.security import create_access_token, get_password_hash, verify_password
from app.auth import get_current_user
from app.redis_model import User
from redis_om.model.model import NotFoundError
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/signup", response_model=StandardResponse, status_code=status.HTTP_201_CREATED)
def signup(user_in: UserCreate):
    try:
        if User.find(User.username == user_in.username).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists")
    except NotFoundError:
        pass  # username not found — good to go

    try:
        if User.find(User.email == user_in.email).first():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists")
    except NotFoundError:
        pass  # email not found — good to go

    # proceed as normal
    hashed_pw = get_password_hash(user_in.password)
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        password_hash=hashed_pw
    )
    new_user.save()

    token = create_access_token({"sub": new_user.id})

    user_dict = {
        "id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "created_at": new_user.created_at.isoformat(),
        "pass": user_in.password
    }

    return StandardResponse(
        message="User created successfully",
        data={"user": user_dict, "access_token": token}
    )

@router.post("/login", response_model=Token)
def login(credentials: UserLogin):
    user = User.find(User.username == credentials.username).first()
    if not user or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token({"sub": user.id})

    user_dict = {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "created_at": user.created_at.isoformat()
    }

    return Token(
        access_token=access_token,
        token_type="bearer",
        user=UserResponse(**user_dict)
    )


@router.get("/me", response_model=UserResponse)
def current_user_info(current_user: User = Depends(get_current_user)):

    user_dict = {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "created_at": current_user.created_at
    }
    return UserResponse(**user_dict)
