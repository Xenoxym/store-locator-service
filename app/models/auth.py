from sqlalchemy import (
    Column,
    String,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Role(Base):
    __tablename__ = "roles"

    role_id = Column(String(50), primary_key=True)
    name = Column(String(50), nullable=False, unique=True)

    users = relationship("User", back_populates="role")
    permissions = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
    )


class Permission(Base):
    __tablename__ = "permissions"

    permission_id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)

    roles = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
    )


class RolePermission(Base):
    __tablename__ = "role_permissions"

    id = Column(String(100), primary_key=True)

    role_id = Column(String(50), ForeignKey("roles.role_id"), nullable=False)
    permission_id = Column(String(50), ForeignKey("permissions.permission_id"), nullable=False)

    role = relationship("Role", back_populates="permissions")
    permission = relationship("Permission", back_populates="roles")


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    token_id = Column(String(100), primary_key=True)
    user_id = Column(String(10), ForeignKey("users.user_id"), nullable=False)

    token_hash = Column(String(255), nullable=False, unique=True)
    is_revoked = Column(Boolean, nullable=False, default=False)

    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("idx_refresh_tokens_token_hash", "token_hash"),
    )