import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.auth import Role, Permission, RolePermission
from app.models.store import Store, StoreService
from app.models.user import User
from app.core.security import hash_password


TEST_DATABASE_URL = "sqlite://"


test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.drop_all(bind=test_engine)
    Base.metadata.create_all(bind=test_engine)

    db = TestingSessionLocal()

    seed_roles_permissions_users(db)
    seed_stores(db)

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def seed_roles_permissions_users(db):
    roles = [
        Role(role_id="admin", name="admin"),
        Role(role_id="marketer", name="marketer"),
        Role(role_id="viewer", name="viewer"),
    ]

    permissions = [
        Permission(permission_id="manage_stores", name="manage_stores"),
        Permission(permission_id="read_stores", name="read_stores"),
        Permission(permission_id="import_stores", name="import_stores"),
        Permission(permission_id="manage_users", name="manage_users"),
    ]

    db.add_all(roles)
    db.add_all(permissions)
    db.flush()

    role_permissions = {
        "admin": ["manage_stores", "read_stores", "import_stores", "manage_users"],
        "marketer": ["manage_stores", "read_stores", "import_stores"],
        "viewer": ["read_stores"],
    }

    for role_id, permission_ids in role_permissions.items():
        for permission_id in permission_ids:
            db.add(
                RolePermission(
                    id=f"{role_id}:{permission_id}",
                    role_id=role_id,
                    permission_id=permission_id,
                )
            )

    db.add_all(
        [
            User(
                user_id="U001",
                email="admin@test.com",
                password_hash=hash_password("AdminTest123!"),
                role_id="admin",
                is_active=True,
                must_change_password=False,
            ),
            User(
                user_id="U002",
                email="marketer@test.com",
                password_hash=hash_password("MarketerTest123!"),
                role_id="marketer",
                is_active=True,
                must_change_password=False,
            ),
            User(
                user_id="U003",
                email="viewer@test.com",
                password_hash=hash_password("ViewerTest123!"),
                role_id="viewer",
                is_active=True,
                must_change_password=False,
            ),
        ]
    )

    db.commit()


def add_store(
    db,
    store_id,
    name,
    store_type,
    status,
    latitude,
    longitude,
    postal_code,
    city,
    state,
    services,
    hours="00:00-23:59",
):
    store = Store(
        store_id=store_id,
        name=name,
        store_type=store_type,
        status=status,
        latitude=latitude,
        longitude=longitude,
        address_street=f"{store_id} Test Street",
        address_city=city,
        address_state=state,
        address_postal_code=postal_code,
        address_country="USA",
        phone="212-555-0100",
        hours_mon=hours,
        hours_tue=hours,
        hours_wed=hours,
        hours_thu=hours,
        hours_fri=hours,
        hours_sat=hours,
        hours_sun=hours,
    )

    db.add(store)
    db.flush()

    for service_name in services:
        db.add(
            StoreService(
                id=str(uuid.uuid4()),
                store_id=store_id,
                service_name=service_name,
            )
        )


def seed_stores(db):
    # New York area
    add_store(
        db=db,
        store_id="S0001",
        name="NY Downtown Store",
        store_type="regular",
        status="active",
        latitude=40.7505,
        longitude=-73.9934,
        postal_code="10001",
        city="New York",
        state="NY",
        services=["pharmacy", "pickup", "returns"],
    )

    add_store(
        db=db,
        store_id="S0002",
        name="NY Express Store",
        store_type="express",
        status="active",
        latitude=40.7520,
        longitude=-73.9900,
        postal_code="10001",
        city="New York",
        state="NY",
        services=["pickup"],
    )

    add_store(
        db=db,
        store_id="S0003",
        name="NY Outlet Store",
        store_type="outlet",
        status="inactive",
        latitude=40.7550,
        longitude=-73.9950,
        postal_code="10001",
        city="New York",
        state="NY",
        services=["returns"],
    )

    # Boston area
    add_store(
        db=db,
        store_id="S0004",
        name="Boston Store",
        store_type="flagship",
        status="active",
        latitude=42.3601,
        longitude=-71.0589,
        postal_code="02114",
        city="Boston",
        state="MA",
        services=["pharmacy", "optical"],
    )

    # Far away store
    add_store(
        db=db,
        store_id="S0005",
        name="LA Store",
        store_type="regular",
        status="active",
        latitude=34.0522,
        longitude=-118.2437,
        postal_code="90001",
        city="Los Angeles",
        state="CA",
        services=["garden_center", "automotive"],
    )

    db.commit()


def login_and_get_tokens(client, email, password):
    response = client.post(
        "/api/auth/login",
        json={
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 200
    return response.json()


@pytest.fixture
def admin_tokens(client):
    return login_and_get_tokens(client, "admin@test.com", "AdminTest123!")


@pytest.fixture
def marketer_tokens(client):
    return login_and_get_tokens(client, "marketer@test.com", "MarketerTest123!")


@pytest.fixture
def viewer_tokens(client):
    return login_and_get_tokens(client, "viewer@test.com", "ViewerTest123!")


@pytest.fixture
def admin_headers(admin_tokens):
    return {"Authorization": f"Bearer {admin_tokens['access_token']}"}


@pytest.fixture
def marketer_headers(marketer_tokens):
    return {"Authorization": f"Bearer {marketer_tokens['access_token']}"}


@pytest.fixture
def viewer_headers(viewer_tokens):
    return {"Authorization": f"Bearer {viewer_tokens['access_token']}"}