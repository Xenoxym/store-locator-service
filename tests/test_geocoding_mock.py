from unittest.mock import MagicMock, patch

from app.services.geocoding import (
    geocode_zip_with_zippopotamus,
    geocode_with_us_census,
    geocode_postal_code,
)


def test_geocode_zip_with_zippopotamus_success():
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "post code": "10001",
        "country": "United States",
        "places": [
            {
                "place name": "New York",
                "state abbreviation": "NY",
                "latitude": "40.7506",
                "longitude": "-73.9972",
            }
        ],
    }
    mock_response.raise_for_status.return_value = None

    with patch("app.services.geocoding.requests.get", return_value=mock_response):
        result = geocode_zip_with_zippopotamus("10001")

    assert result["source"] == "zippopotamus"
    assert result["lat"] == 40.7506
    assert result["lon"] == -73.9972
    assert "10001" in result["display_name"]


def test_geocode_zip_with_zippopotamus_404_returns_none():
    mock_response = MagicMock()
    mock_response.status_code = 404

    with patch("app.services.geocoding.requests.get", return_value=mock_response):
        result = geocode_zip_with_zippopotamus("00000")

    assert result is None


def test_geocode_with_us_census_success():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {
            "addressMatches": [
                {
                    "matchedAddress": "4600 SILVER HILL RD, WASHINGTON, DC, 20233",
                    "coordinates": {
                        "x": -76.92744,
                        "y": 38.845985,
                    },
                }
            ]
        }
    }
    mock_response.raise_for_status.return_value = None

    with patch("app.services.geocoding.requests.get", return_value=mock_response):
        result = geocode_with_us_census("4600 Silver Hill Rd, Washington, DC 20233")

    assert result["source"] == "us_census"
    assert result["lat"] == 38.845985
    assert result["lon"] == -76.92744


def test_geocode_with_us_census_no_match_returns_none():
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "result": {
            "addressMatches": []
        }
    }
    mock_response.raise_for_status.return_value = None

    with patch("app.services.geocoding.requests.get", return_value=mock_response):
        result = geocode_with_us_census("not a real address")

    assert result is None


def test_geocode_postal_code_uses_cache_before_external_api(db_session):
    cached_value = {
        "lat": 40.75,
        "lon": -73.99,
        "display_name": "cached zip",
        "source": "redis_cache",
    }

    with patch("app.services.geocoding.get_cache", return_value=cached_value) as mock_get_cache:
        with patch("app.services.geocoding.geocode_zip_with_zippopotamus") as mock_zip_api:
            result = geocode_postal_code(db_session, "10001")

    assert result == cached_value
    mock_get_cache.assert_called_once()
    mock_zip_api.assert_not_called()