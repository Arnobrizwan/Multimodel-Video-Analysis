"""Authentication and authorization module"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel, validator
import os

# Security configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()

# In-memory user store (replace with database in production)
users_db = {}
# In-memory session store for demo users
demo_sessions = {}


# ==================== Models ====================
class User(BaseModel):
    user_id: str
    username: str
    email: Optional[str] = None


class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

    @validator('username')
    def validate_username(cls, v):
        """Validate username format and length"""
        import re

        # Length check
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 50:
            raise ValueError("Username too long (max 50 characters)")

        # Alphanumeric and underscores only
        if not re.match(r'^[\w]+$', v):
            raise ValueError("Username can only contain letters, numbers, and underscores")

        # No SQL injection patterns
        dangerous_patterns = ['--', ';', 'DROP', 'DELETE', 'INSERT', 'UPDATE', 'SELECT']
        v_upper = v.upper()
        if any(pattern in v_upper for pattern in dangerous_patterns):
            raise ValueError("Username contains invalid patterns")

        return v

    @validator('password')
    def validate_password(cls, v):
        """Validate password strength"""
        # Length check
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if len(v) > 128:
            raise ValueError("Password too long (max 128 characters)")

        # Require complexity
        has_upper = any(c.isupper() for c in v)
        has_lower = any(c.islower() for c in v)
        has_digit = any(c.isdigit() for c in v)

        if not (has_upper and has_lower and has_digit):
            raise ValueError(
                "Password must contain at least one uppercase letter, "
                "one lowercase letter, and one digit"
            )

        return v

    @validator('email')
    def validate_email(cls, v):
        """Validate email format"""
        if v is None:
            return v

        import re

        # Length check
        if len(v) > 254:
            raise ValueError("Email too long (max 254 characters)")

        # Basic email regex
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, v):
            raise ValueError("Invalid email format")

        return v.lower()


class Token(BaseModel):
    access_token: str
    token_type: str
    user_id: str


class TokenData(BaseModel):
    user_id: Optional[str] = None


# ==================== Helper Functions ====================
def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash password"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Create JWT access token"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_demo_session() -> str:
    """Create anonymous demo session"""
    import uuid
    session_id = str(uuid.uuid4())
    user_id = f"demo_{session_id[:8]}"

    # Create demo user
    demo_sessions[session_id] = {
        "user_id": user_id,
        "created_at": datetime.utcnow(),
        "username": f"demo_user_{session_id[:8]}"
    }

    # Create token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user_id, "session_id": session_id},
        expires_delta=access_token_expires
    )

    return access_token, user_id


def authenticate_user(username: str, password: str) -> Optional[dict]:
    """Authenticate user with username and password"""
    if username not in users_db:
        return None
    user = users_db[username]
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def create_user(username: str, password: str, email: Optional[str] = None) -> dict:
    """Create new user"""
    if username in users_db:
        raise ValueError("Username already exists")

    import uuid
    user_id = str(uuid.uuid4())
    hashed_password = get_password_hash(password)

    user = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow()
    }

    users_db[username] = user
    return user


# ==================== Dependencies ====================
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from token"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
    except JWTError:
        raise credentials_exception

    # Check if it's a demo session
    session_id = payload.get("session_id")
    if session_id and session_id in demo_sessions:
        session = demo_sessions[session_id]
        return User(
            user_id=session["user_id"],
            username=session["username"]
        )

    # Check regular users
    user = None
    for username, user_data in users_db.items():
        if user_data["user_id"] == token_data.user_id:
            user = User(
                user_id=user_data["user_id"],
                username=user_data["username"],
                email=user_data.get("email")
            )
            break

    if user is None:
        raise credentials_exception

    return user


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))
) -> Optional[User]:
    """Get current user if authenticated, None otherwise"""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
