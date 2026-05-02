from unittest.mock import patch


VALID_CSV = """store_id,name,store_type,status,latitude,longitude,address_street,address_city,address_state,address_postal_code,address_country,phone,services,hours_mon,hours_tue,hours_wed,hours_thu,hours_fri,hours_sat,hours_sun
S0200,CSV Test Store,regular,active,40.7600,-73.9800,200 CSV Street,New York,NY,10001,USA,212-555-0200,pickup|returns,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,09:00-21:00,10:00-20:00
"""


INVALID_HEADER_CSV = """storeid,name,store_type,status,latitude,longitude,address_street,address_city,address_state,address_postal_code,address_country,phone,services,hours_mon,hours_tue,hours_wed,hours_thu,hours_fri,hours_sat,hours_sun
S0201,Bad CSV Store,regular,active,40.7600,-73.9800,201 CSV Street,New York,NY,10001,USA,212-555-0201,pickup,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,09:00-21:00,10:00-20:00
"""


INVALID_ROW_CSV = """store_id,name,store_type,status,latitude,longitude,address_street,address_city,address_state,address_postal_code,address_country,phone,services,hours_mon,hours_tue,hours_wed,hours_thu,hours_fri,hours_sat,hours_sun
S0202,Bad Row Store,wrong_type,active,999,-73.9800,202 CSV Street,New York,NY,10001,USA,212-555-0202,pickup,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,09:00-21:00,10:00-20:00
"""

CSV_MISSING_COORDINATES = """store_id,name,store_type,status,address_street,address_city,address_state,address_postal_code,address_country,phone,services,hours_mon,hours_tue,hours_wed,hours_thu,hours_fri,hours_sat,hours_sun
S0400,CSV Auto Geocoded Store,regular,active,350 5th Ave,New York,NY,10118,USA,212-555-0400,pickup|returns,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,08:00-22:00,09:00-21:00,10:00-20:00
"""

def test_admin_can_import_valid_csv(client, admin_headers):
    files = {
        "file": (
            "stores.csv",
            VALID_CSV,
            "text/csv",
        )
    }

    response = client.post(
        "/api/admin/stores/import",
        headers=admin_headers,
        files=files,
    )

    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["created"] == 1
    assert data["updated"] == 0
    assert data["failed"] == 0


def test_csv_import_upserts_existing_store(client, admin_headers):
    files = {
        "file": (
            "stores.csv",
            VALID_CSV,
            "text/csv",
        )
    }

    first_response = client.post(
        "/api/admin/stores/import",
        headers=admin_headers,
        files=files,
    )
    assert first_response.status_code == 200

    second_response = client.post(
        "/api/admin/stores/import",
        headers=admin_headers,
        files=files,
    )
    assert second_response.status_code == 200

    data = second_response.json()
    assert data["created"] == 0
    assert data["updated"] == 1


def test_viewer_cannot_import_csv(client, viewer_headers):
    files = {
        "file": (
            "stores.csv",
            VALID_CSV,
            "text/csv",
        )
    }

    response = client.post(
        "/api/admin/stores/import",
        headers=viewer_headers,
        files=files,
    )

    assert response.status_code == 403


def test_csv_import_rejects_invalid_header(client, admin_headers):
    files = {
        "file": (
            "bad_stores.csv",
            INVALID_HEADER_CSV,
            "text/csv",
        )
    }

    response = client.post(
        "/api/admin/stores/import",
        headers=admin_headers,
        files=files,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["success"] is False


def test_csv_import_rejects_invalid_row(client, admin_headers):
    files = {
        "file": (
            "bad_row.csv",
            INVALID_ROW_CSV,
            "text/csv",
        )
    }

    response = client.post(
        "/api/admin/stores/import",
        headers=admin_headers,
        files=files,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["success"] is False
    assert response.json()["detail"]["failed"] == 1


def test_csv_import_rejects_non_csv_file(client, admin_headers):
    files = {
        "file": (
            "stores.txt",
            VALID_CSV,
            "text/plain",
        )
    }

    response = client.post(
        "/api/admin/stores/import",
        headers=admin_headers,
        files=files,
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only CSV files are allowed"


def test_integration_csv_import_then_search_with_mocked_geocoding(client, admin_headers):
    files = {
        "file": (
            "stores.csv",
            VALID_CSV,
            "text/csv",
        )
    }

    import_response = client.post(
        "/api/admin/stores/import",
        headers=admin_headers,
        files=files,
    )

    assert import_response.status_code == 200

    with patch(
        "app.services.store_search.geocode_postal_code",
        return_value={
            "lat": 40.7600,
            "lon": -73.9800,
            "display_name": "10001, New York, NY",
            "source": "zippopotamus",
        },
    ):
        search_response = client.post(
            "/api/stores/search",
            json={
                "postal_code": "10001",
                "radius_miles": 2,
            },
        )

    assert search_response.status_code == 200

    store_ids = [store["store_id"] for store in search_response.json()["results"]]
    assert "S0200" in store_ids


def test_csv_import_auto_geocodes_missing_coordinates(client, admin_headers):
    files = {
        "file": (
            "stores_missing_coordinates.csv",
            CSV_MISSING_COORDINATES,
            "text/csv",
        )
    }

    with patch(
        "app.services.csv_import.geocode_address",
        return_value={
            "lat": 40.7484,
            "lon": -73.9857,
            "display_name": "350 5th Ave, New York, NY 10118",
            "source": "us_census",
        },
    ):
        response = client.post(
            "/api/admin/stores/import",
            headers=admin_headers,
            files=files,
        )

    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["created"] == 1
    assert data["failed"] == 0

    detail_response = client.get(
        "/api/admin/stores/S0400",
        headers=admin_headers,
    )

    assert detail_response.status_code == 200
    detail = detail_response.json()
    assert detail["latitude"] == 40.7484
    assert detail["longitude"] == -73.9857