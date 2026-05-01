import uuid

from app.db.session import SessionLocal
from app.models.auth import Role, Permission, RolePermission
from app.models.user import User
from app.core.security import hash_password


ROLES = [
    ("admin", "admin"),
    ("marketer", "marketer"),
    ("viewer", "viewer"),
]


PERMISSIONS = [
    ("manage_stores", "manage_stores"),
    ("read_stores", "read_stores"),
    ("import_stores", "import_stores"),
    ("manage_users", "manage_users"),
]


ROLE_PERMISSIONS = {
    "admin": ["manage_stores", "read_stores", "import_stores", "manage_users"],
    "marketer": ["manage_stores", "read_stores", "import_stores"],
    "viewer": ["read_stores"],
}


USERS = [
    {
        "user_id": "U001",
        "email": "admin@test.com",
        "password": "AdminTest123!",
        "role_id": "admin",
    },
    {
        "user_id": "U002",
        "email": "marketer@test.com",
        "password": "MarketerTest123!",
        "role_id": "marketer",
    },
    {
        "user_id": "U003",
        "email": "viewer@test.com",
        "password": "ViewerTest123!",
        "role_id": "viewer",
    },
]


def seed_users():
    db = SessionLocal()

    try:
        for role_id, name in ROLES:
            existing = db.query(Role).filter(Role.role_id == role_id).first()
            if not existing:
                db.add(Role(role_id=role_id, name=name))

        for permission_id, name in PERMISSIONS:
            existing = (
                db.query(Permission)
                .filter(Permission.permission_id == permission_id)
                .first()
            )
            if not existing:
                db.add(Permission(permission_id=permission_id, name=name))

        db.flush()

        for role_id, permissions in ROLE_PERMISSIONS.items():
            for permission_id in permissions:
                rp_id = f"{role_id}:{permission_id}"
                existing = (
                    db.query(RolePermission)
                    .filter(RolePermission.id == rp_id)
                    .first()
                )
                if not existing:
                    db.add(
                        RolePermission(
                            id=rp_id,
                            role_id=role_id,
                            permission_id=permission_id,
                        )
                    )

        for user_data in USERS:
            existing = (
                db.query(User)
                .filter(User.email == user_data["email"])
                .first()
            )

            if not existing:
                db.add(
                    User(
                        user_id=user_data["user_id"],
                        email=user_data["email"],
                        password_hash=hash_password(user_data["password"]),
                        role_id=user_data["role_id"],
                        is_active=True,
                        must_change_password=False,
                    )
                )

        db.commit()

        print("Seed users completed.")
        print("Admin: admin@test.com / AdminTest123!")
        print("Marketer: marketer@test.com / MarketerTest123!")
        print("Viewer: viewer@test.com / ViewerTest123!")

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()


if __name__ == "__main__":
    seed_users()