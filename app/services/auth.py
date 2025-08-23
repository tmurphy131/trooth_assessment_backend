from firebase_admin import auth
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth
from app.db import get_db
from app.models.user import User, UserRole
from sqlalchemy.orm import Session
import datetime
from app.schemas.user import UserSchema

security = HTTPBearer()

def verify_token(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authorization header missing or invalid")
    id_token = auth_header.split(" ")[1]
    try:
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

def require_role(role: str):
    def role_checker(decoded_token=Depends(verify_token)):
        if decoded_token.get("role") != role:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Insufficient role")
        return decoded_token
    return role_checker

def require_roles(roles: list):
    def role_checker(decoded_token=Depends(verify_token)):
        if decoded_token.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden: Insufficient role")
        return decoded_token
    return role_checker

def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    
    token = credentials.credentials
    # Test tokens for development
    if token == "mock-mentor-token":
        return User(id="mentor-1", name="Mentor One", email="mentor@example.com", role=UserRole.mentor, created_at=datetime.datetime.utcnow())
    elif token == "mock-apprentice-token":
        return User(id="apprentice-1", name="Apprentice One", email="apprentice@example.com", role=UserRole.apprentice, created_at=datetime.datetime.utcnow())
    elif token == "mock-admin-token":
        return User(id="admin-1", name="Admin One", email="admin@example.com", role=UserRole.admin, created_at=datetime.datetime.utcnow())
    
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        user_id = decoded_token["uid"]
        email = decoded_token["email"]
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired Firebase token",
        )

    # First try to find user by Firebase UID
    user = db.query(User).filter(User.id == user_id).first()
    
    # If not found by UID, try to find by email (for existing users)
    if not user:
        user = db.query(User).filter(User.email == email).first()
        if user:
            # Update the user's ID to match Firebase UID
            user.id = user_id
            db.commit()
            return user
    
    # If still not found, create a new user
    if not user:
        # Default to apprentice role for new users
        from app.models.user import User as UserModel, UserRole
        user = UserModel(
            id=user_id,
            email=email,
            name=email.split('@')[0].title(),  # Use email prefix as name
            role=UserRole.apprentice  # Default role
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    
    return user

def require_mentor(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.mentor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mentor access required"
        )
    return user

def require_apprentice(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.apprentice:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apprentice access required"
        )
    return user

def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != UserRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )
    return user

def require_mentor_or_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in {UserRole.mentor, UserRole.admin}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Mentors or admins only"
        )
    return user