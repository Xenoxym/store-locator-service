from unittest.mock import patch


def test_search_by_coordinates(client):
    response = client.post(
        "/api/stores/search",
        json={
            "latitude": 40.7505,
            "longitude": -73.9934,
            "radius_miles": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["result_count"] >= 1
    assert data["results"][0]["store_id"] == "S0001"


def test_search_by_postal_code_with_mocked_geocoding(client):
    with patch(
        "app.services.store_search.geocode_postal_code",
        return_value={
            "lat": 40.7505,
            "lon": -73.9934,
            "display_name": "10001, New York, NY",
            "source": "zippopotamus",
        },
    ):
        response = client.post(
            "/api/stores/search",
            json={
                "postal_code": "10001",
                "radius_miles": 5,
            },
        )

    assert response.status_code == 200

    data = response.json()
    assert data["searched_location"]["source"] == "zippopotamus"
    assert data["result_count"] >= 1


def test_search_by_address_with_mocked_geocoding(client):
    with patch(
        "app.services.store_search.geocode_address",
        return_value={
            "lat": 40.7505,
            "lon": -73.9934,
            "display_name": "New York, NY",
            "source": "us_census",
        },
    ):
        response = client.post(
            "/api/stores/search",
            json={
                "address": "New York, NY",
                "radius_miles": 5,
            },
        )

    assert response.status_code == 200

    data = response.json()
    assert data["searched_location"]["source"] == "us_census"
    assert data["result_count"] >= 1


def test_search_services_and_filter(client):
    response = client.post(
        "/api/stores/search",
        json={
            "latitude": 40.7505,
            "longitude": -73.9934,
            "radius_miles": 5,
            "services": ["pharmacy", "pickup"],
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["result_count"] >= 1

    for store in data["results"]:
        assert "pharmacy" in store["services"]
        assert "pickup" in store["services"]


def test_search_store_types_or_filter(client):
    response = client.post(
        "/api/stores/search",
        json={
            "latitude": 40.7505,
            "longitude": -73.9934,
            "radius_miles": 5,
            "store_types": ["express"],
        },
    )

    assert response.status_code == 200

    data = response.json()

    for store in data["results"]:
        assert store["store_type"] == "express"


def test_search_does_not_return_inactive_stores(client):
    response = client.post(
        "/api/stores/search",
        json={
            "latitude": 40.7505,
            "longitude": -73.9934,
            "radius_miles": 5,
        },
    )

    assert response.status_code == 200

    data = response.json()
    returned_ids = [store["store_id"] for store in data["results"]]

    assert "S0003" not in returned_ids


def test_search_requires_exactly_one_input_type(client):
    response = client.post(
        "/api/stores/search",
        json={
            "postal_code": "10001",
            "latitude": 40.7505,
            "longitude": -73.9934,
            "radius_miles": 5,
        },
    )

    assert response.status_code == 422