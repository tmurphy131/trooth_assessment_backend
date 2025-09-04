from firebase_admin import auth
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import auth as firebase_auth
from app.db import get_db
from app.models.user import User, UserRole
from sqlalchemy.orm import Session
from datetime import UTC, datetime
from app.utils.datetime import utc_now
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
    # Test tokens for development (ensure persistence so FK constraints pass)
    mock_map = {
        "mock-mentor-token": ("mentor-1", "Mentor One", "mentor@example.com", UserRole.mentor),
        "mock-apprentice-token": ("apprentice-1", "Apprentice One", "apprentice@example.com", UserRole.apprentice),
        "mock-admin-token": ("admin-1", "Admin One", "admin@example.com", UserRole.admin),
    }
    if token in mock_map:
        uid, name, email, role = mock_map[token]
        user = db.query(User).filter(User.id == uid).first()
        if not user:
            user = User(id=uid, name=name, email=email, role=role, created_at=utc_now())
            db.add(user)
            db.commit()
            db.refresh(user)
        return user
    
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        user_id = decoded_token["uid"]
        email = decoded_token["email"]
        # Try to get full name from token
        full_name = None
        if "name" in decoded_token:
            full_name = decoded_token["name"]
        else:
            # Try to build from given_name and family_name if available
            given = decoded_token.get("given_name", "")
            family = decoded_token.get("family_name", "")
            if given or family:
                full_name = (given + " " + family).strip()
        # Try to get role from token (custom claim)
        role_from_token = decoded_token.get("role")
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
        if role_from_token == "mentor":
            user_role = UserRole.mentor
        elif role_from_token == "admin":
            user_role = UserRole.admin
        else:
            user_role = UserRole.apprentice
        user = User(
            id=user_id,
            email=email,
            name=full_name if full_name else email.split('@')[0].title(),
            role=user_role
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