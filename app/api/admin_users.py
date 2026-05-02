import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.core.security import hash_password
from app.db.session import get_db
from app.models.auth import Role
from app.models.user import User
from app.schemas.admin_user import (
    AdminUserCreate,
    AdminUserUpdate,
    AdminUserResponse,
    UserListResponse,
)


router = APIRouter(
    prefix="/api/admin/users",
    tags=["Admin Users"],
)


def generate_user_id() -> str:
    """
    Generate a short user_id compatible with User.user_id String(10).
    Example: U1A2B3C4D
    """
    return "U" + uuid.uuid4().hex[:8].upper()


def serialize_user(user: User) -> dict:
    return {
        "user_id": user.user_id,
        "email": user.email,
        "role_id": user.role_id,
        "role_name": user.role.name if user.role else user.role_id,
        "is_active": user.is_active,
        "must_change_password": user.must_change_password,
    }


def validate_role_exists(db: Session, role_id: str) -> Role:
    role = db.query(Role).filter(Role.role_id == role_id).first()

    if not role:
        raise HTTPException(status_code=400, detail=f"Invalid role_id: {role_id}")

    return role


@router.post("", response_model=AdminUserResponse, status_code=201)
def create_user(
    request: AdminUserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
):
    validate_role_exists(db, request.role_id)

    existing_user = db.query(User).filter(User.email == request.email).first()

    if existing_user:
        raise HTTPException(status_code=400, detail="User email already exists")

    user = User(
        user_id=generate_user_id(),
        email=request.email,
        password_hash=hash_password(request.password),
        role_id=request.role_id,
        is_active=True,
        must_change_password=True,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return serialize_user(user)


@router.get("", response_model=UserListResponse)
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
):
    total = db.query(User).count()

    users = (
        db.query(User)
        .order_by(User.user_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [serialize_user(user) for user in users],
    }


@router.put("/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: str,
    request: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
):
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = request.model_dump(exclude_unset=True)

    if "role_id" in update_data:
        validate_role_exists(db, update_data["role_id"])
        user.role_id = update_data["role_id"]

    if "is_active" in update_data:
        user.is_active = update_data["is_active"]

    db.commit()
    db.refresh(user)

    return serialize_user(user)


@router.delete("/{user_id}")
def deactivate_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin"])),
):
    user = db.query(User).filter(User.user_id == user_id).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()

    return {
        "message": "User deactivated successfully",
        "user_id": user_id,
        "is_active": False,
    }