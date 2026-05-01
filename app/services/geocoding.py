import requests
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.store import Store
from app.services.cache import get_cache, set_cache


def _normalize_text(value: str) -> str:
    return value.strip().lower()


def _parse_census_coordinates(data: dict) -> dict | None:
    """
    Parse US Census Geocoder response.

    Expected response path:
    result -> addressMatches -> [0] -> coordinates -> {x, y}

    x = longitude
    y = latitude
    """
    matches = data.get("result", {}).get("addressMatches", [])

    if not matches:
        return None

    first_match = matches[0]
    coordinates = first_match.get("coordinates", {})

    lon = coordinates.get("x")
    lat = coordinates.get("y")

    if lat is None or lon is None:
        return None

    return {
        "lat": float(lat),
        "lon": float(lon),
        "display_name": first_match.get("matchedAddress", "US Census match"),
        "source": "us_census",
    }


def geocode_with_us_census(oneline_address: str) -> dict | None:
    """
    Call US Census single-line address geocoder.

    API docs:
    https://geocoding.geo.census.gov/geocoder/Geocoding_Services_API.html
    """
    params = {
        "address": oneline_address,
        "benchmark": settings.US_CENSUS_BENCHMARK,
        "format": "json",
    }

    try:
        response = requests.get(
            settings.US_CENSUS_GEOCODER_URL,
            params=params,
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return None

    return _parse_census_coordinates(data)


def geocode_zip_with_zippopotamus(postal_code: str) -> dict | None:
    """
    Resolve US ZIP code to coordinates using Zippopotam.us.

    Example:
    GET https://api.zippopotam.us/us/10001
    """
    url = f"{settings.ZIPPOPOTAMUS_URL}/{postal_code}"

    try:
        response = requests.get(url, timeout=5)

        if response.status_code == 404:
            return None

        response.raise_for_status()
        data = response.json()

    except Exception:
        return None

    places = data.get("places", [])

    if not places:
        return None

    first_place = places[0]

    latitude = first_place.get("latitude")
    longitude = first_place.get("longitude")

    if latitude is None or longitude is None:
        return None

    return {
        "lat": float(latitude),
        "lon": float(longitude),
        "display_name": f"{data.get('post code')}, {first_place.get('place name')}, {first_place.get('state abbreviation')}",
        "source": "zippopotamus",
    }


def fallback_geocode_postal_code_from_db(db: Session, postal_code: str) -> dict | None:
    """
    Local fallback:
    Find one active store with the same ZIP code and use its coordinates.
    This keeps demo stable if Census does not resolve ZIP-only input.
    """
    store = (
        db.query(Store)
        .filter(Store.address_postal_code == postal_code)
        .filter(Store.status == "active")
        .first()
    )

    if not store:
        return None

    return {
        "lat": store.latitude,
        "lon": store.longitude,
        "display_name": f"ZIP {postal_code}",
        "source": "local_database_fallback",
    }


def fallback_geocode_address_from_db(db: Session, address: str) -> dict | None:
    """
    Local fallback:
    Search address fields from existing stores.
    """
    keyword = f"%{address}%"

    store = (
        db.query(Store)
        .filter(Store.status == "active")
        .filter(
            (Store.address_street.ilike(keyword))
            | (Store.address_city.ilike(keyword))
            | (Store.address_state.ilike(keyword))
            | (Store.address_postal_code.ilike(keyword))
        )
        .first()
    )

    if not store:
        return None

    return {
        "lat": store.latitude,
        "lon": store.longitude,
        "display_name": address,
        "source": "local_database_fallback",
    }


def geocode_postal_code(db: Session, postal_code: str) -> dict:
    """
    Resolve postal code to coordinates.

    Flow:
    1. Redis cache
    2. Zippopotam.us ZIP lookup
    3. Local database fallback
    """
    normalized_zip = postal_code.strip()
    cache_key = f"geocode:zip:{normalized_zip}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    result = geocode_zip_with_zippopotamus(normalized_zip)

    if result is None:
        result = fallback_geocode_postal_code_from_db(db, normalized_zip)

    if result is None:
        raise ValueError(f"No coordinates found for postal code: {postal_code}")

    set_cache(
        cache_key,
        result,
        settings.GEOCODING_CACHE_TTL_SECONDS,
    )

    return result


def geocode_address(db: Session, address: str) -> dict:
    """
    Resolve full address / city / state / ZIP-like text to coordinates.

    Flow:
    1. Redis cache
    2. US Census Geocoder
    3. Local database fallback
    """
    normalized_address = _normalize_text(address)
    cache_key = f"geocode:address:{normalized_address}"

    cached = get_cache(cache_key)
    if cached:
        return cached

    result = geocode_with_us_census(address)

    if result is None:
        result = fallback_geocode_address_from_db(db, address)

    if result is None:
        raise ValueError(f"No coordinates found for address: {address}")

    set_cache(
        cache_key,
        result,
        settings.GEOCODING_CACHE_TTL_SECONDS,
    )

    return result