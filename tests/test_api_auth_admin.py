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