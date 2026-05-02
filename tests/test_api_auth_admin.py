from unittest.mock import patch

def test_login_success(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@test.com",
            "password": "AdminTest123!",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_failure_wrong_password(client):
    response = client.post(
        "/api/auth/login",
        json={
            "email": "admin@test.com",
            "password": "WrongPassword123!",
        },
    )

    assert response.status_code == 401


def test_refresh_token_success(client, admin_tokens):
    response = client.post(
        "/api/auth/refresh",
        json={
            "refresh_token": admin_tokens["refresh_token"],
        },
    )

    assert response.status_code == 200
    assert "access_token" in response.json()


def test_logout_revokes_refresh_token(client, admin_tokens):
    refresh_token = admin_tokens["refresh_token"]

    logout_response = client.post(
        "/api/auth/logout",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert logout_response.status_code == 200

    refresh_response = client.post(
        "/api/auth/refresh",
        json={
            "refresh_token": refresh_token,
        },
    )

    assert refresh_response.status_code == 401


def test_admin_can_list_stores(client, admin_headers):
    response = client.get(
        "/api/admin/stores?page=1&page_size=10",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 5
    assert len(data["results"]) <= 10


def test_viewer_can_list_stores(client, viewer_headers):
    response = client.get(
        "/api/admin/stores?page=1&page_size=10",
        headers=viewer_headers,
    )

    assert response.status_code == 200


def test_unauthenticated_user_cannot_list_stores(client):
    response = client.get("/api/admin/stores?page=1&page_size=10")

    assert response.status_code in (401, 403)


def test_admin_can_create_store(client, admin_headers):
    response = client.post(
        "/api/admin/stores",
        headers=admin_headers,
        json={
            "store_id": "S0100",
            "name": "Created Test Store",
            "store_type": "regular",
            "status": "active",
            "latitude": 40.7600,
            "longitude": -73.9800,
            "address_street": "100 Create Street",
            "address_city": "New York",
            "address_state": "NY",
            "address_postal_code": "10001",
            "address_country": "USA",
            "phone": "212-555-0100",
            "services": ["pickup", "returns"],
            "hours_mon": "08:00-22:00",
            "hours_tue": "08:00-22:00",
            "hours_wed": "08:00-22:00",
            "hours_thu": "08:00-22:00",
            "hours_fri": "08:00-22:00",
            "hours_sat": "09:00-21:00",
            "hours_sun": "10:00-20:00",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["store_id"] == "S0100"
    assert data["services"] == ["pickup", "returns"]


def test_viewer_cannot_create_store(client, viewer_headers):
    response = client.post(
        "/api/admin/stores",
        headers=viewer_headers,
        json={
            "store_id": "S0101",
            "name": "Viewer Should Fail",
            "store_type": "regular",
            "status": "active",
            "latitude": 40.7600,
            "longitude": -73.9800,
            "address_street": "101 Fail Street",
            "address_city": "New York",
            "address_state": "NY",
            "address_postal_code": "10001",
            "address_country": "USA",
            "phone": "212-555-0101",
            "services": ["pickup"],
            "hours_mon": "08:00-22:00",
            "hours_tue": "08:00-22:00",
            "hours_wed": "08:00-22:00",
            "hours_thu": "08:00-22:00",
            "hours_fri": "08:00-22:00",
            "hours_sat": "09:00-21:00",
            "hours_sun": "10:00-20:00",
        },
    )

    assert response.status_code == 403


def test_marketer_can_patch_store(client, marketer_headers):
    response = client.patch(
        "/api/admin/stores/S0001",
        headers=marketer_headers,
        json={
            "name": "Updated Name",
            "phone": "212-555-9999",
            "services": ["pharmacy", "pickup"],
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["phone"] == "212-555-9999"
    assert data["services"] == ["pharmacy", "pickup"]


def test_patch_rejects_forbidden_latitude_field(client, admin_headers):
    response = client.patch(
        "/api/admin/stores/S0001",
        headers=admin_headers,
        json={
            "latitude": 41.0000,
        },
    )

    assert response.status_code == 422


def test_delete_soft_deactivates_store(client, admin_headers):
    response = client.delete(
        "/api/admin/stores/S0001",
        headers=admin_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "inactive"

    detail_response = client.get(
        "/api/admin/stores/S0001",
        headers=admin_headers,
    )

    assert detail_response.status_code == 200
    assert detail_response.json()["status"] == "inactive"


def test_admin_can_create_user(client, admin_headers):
    response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": "newuser@test.com",
            "password": "NewUserTest123!",
            "role_id": "viewer",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["email"] == "newuser@test.com"
    assert data["role_id"] == "viewer"
    assert data["is_active"] is True
    assert "password" not in data
    assert "password_hash" not in data


def test_admin_can_list_users(client, admin_headers):
    response = client.get(
        "/api/admin/users?page=1&page_size=10",
        headers=admin_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] >= 3
    assert len(data["results"]) >= 3


def test_admin_can_update_user_role_and_status(client, admin_headers):
    create_response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": "updateuser@test.com",
            "password": "UpdateUserTest123!",
            "role_id": "viewer",
        },
    )

    assert create_response.status_code == 201
    user_id = create_response.json()["user_id"]

    update_response = client.put(
        f"/api/admin/users/{user_id}",
        headers=admin_headers,
        json={
            "role_id": "marketer",
            "is_active": False,
        },
    )

    assert update_response.status_code == 200

    data = update_response.json()
    assert data["role_id"] == "marketer"
    assert data["is_active"] is False


def test_admin_can_deactivate_user(client, admin_headers):
    create_response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": "deleteuser@test.com",
            "password": "DeleteUserTest123!",
            "role_id": "viewer",
        },
    )

    assert create_response.status_code == 201
    user_id = create_response.json()["user_id"]

    delete_response = client.delete(
        f"/api/admin/users/{user_id}",
        headers=admin_headers,
    )

    assert delete_response.status_code == 200
    assert delete_response.json()["is_active"] is False


def test_marketer_cannot_manage_users(client, marketer_headers):
    response = client.get(
        "/api/admin/users?page=1&page_size=10",
        headers=marketer_headers,
    )

    assert response.status_code == 403


def test_viewer_cannot_manage_users(client, viewer_headers):
    response = client.get(
        "/api/admin/users?page=1&page_size=10",
        headers=viewer_headers,
    )

    assert response.status_code == 403


def test_create_user_rejects_duplicate_email(client, admin_headers):
    first_response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": "duplicate@test.com",
            "password": "DuplicateTest123!",
            "role_id": "viewer",
        },
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": "duplicate@test.com",
            "password": "DuplicateTest123!",
            "role_id": "viewer",
        },
    )

    assert second_response.status_code == 400


def test_create_user_rejects_invalid_role(client, admin_headers):
    response = client.post(
        "/api/admin/users",
        headers=admin_headers,
        json={
            "email": "badrole@test.com",
            "password": "BadRoleTest123!",
            "role_id": "superadmin",
        },
    )

    assert response.status_code == 400


def test_update_user_rejects_non_existing_user(client, admin_headers):
    response = client.put(
        "/api/admin/users/U_NO_SUCH",
        headers=admin_headers,
        json={
            "role_id": "viewer",
        },
    )

    assert response.status_code == 404

def test_admin_can_create_store_without_coordinates_using_geocoding(client, admin_headers):
    with patch(
        "app.api.admin_stores.geocode_address",
        return_value={
            "lat": 40.7484,
            "lon": -73.9857,
            "display_name": "350 5th Ave, New York, NY 10118",
            "source": "us_census",
        },
    ):
        response = client.post(
            "/api/admin/stores",
            headers=admin_headers,
            json={
                "store_id": "S0300",
                "name": "Auto Geocoded Test Store",
                "store_type": "regular",
                "status": "active",
                "address_street": "350 5th Ave",
                "address_city": "New York",
                "address_state": "NY",
                "address_postal_code": "10118",
                "address_country": "USA",
                "phone": "212-555-0300",
                "services": ["pickup", "returns"],
                "hours_mon": "08:00-22:00",
                "hours_tue": "08:00-22:00",
                "hours_wed": "08:00-22:00",
                "hours_thu": "08:00-22:00",
                "hours_fri": "08:00-22:00",
                "hours_sat": "09:00-21:00",
                "hours_sun": "10:00-20:00",
            },
        )

    assert response.status_code == 201
    data = response.json()
    assert data["latitude"] == 40.7484
    assert data["longitude"] == -73.9857