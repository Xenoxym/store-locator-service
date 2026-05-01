import hashlib
import json

from sqlalchemy.orm import Session

from app.models.store import Store, StoreService
from app.schemas.store import StoreSearchRequest
from app.services.distance import calculate_bounding_box, calculate_distance_miles
from app.services.hours import is_store_open_now
from app.services.geocoding import geocode_address, geocode_postal_code
from app.services.cache import get_cache, set_cache
from app.core.config import settings



def resolve_search_location(db: Session, request: StoreSearchRequest) -> dict:
    """
    Convert address/postal_code/coordinates into a single lat/lon location.
    """
    if request.latitude is not None and request.longitude is not None:
        return {
            "lat": request.latitude,
            "lon": request.longitude,
            "display_name": "coordinates",
            "source": "request_coordinates",
        }

    if request.postal_code:
        return geocode_postal_code(db, request.postal_code)

    if request.address:
        return geocode_address(db, request.address)

    raise ValueError("Invalid search input.")


def build_search_cache_key(request: StoreSearchRequest) -> str:
    request_data = request.model_dump()
    serialized = json.dumps(request_data, sort_keys=True)
    digest = hashlib.sha256(serialized.encode("utf-8")).hexdigest()
    return f"search:{digest}"


def search_stores(db: Session, request: StoreSearchRequest) -> dict:
    cache_key = build_search_cache_key(request)

    cached_result = get_cache(cache_key)
    if cached_result:
        return cached_result

    location = resolve_search_location(db, request)

    search_lat = location["lat"]
    search_lon = location["lon"]

    box = calculate_bounding_box(
        lat=search_lat,
        lon=search_lon,
        radius_miles=request.radius_miles,
    )

    query = (
        db.query(Store)
        .filter(Store.status == "active")
        .filter(Store.latitude >= box["min_lat"])
        .filter(Store.latitude <= box["max_lat"])
        .filter(Store.longitude >= box["min_lon"])
        .filter(Store.longitude <= box["max_lon"])
    )

    if request.store_types:
        query = query.filter(Store.store_type.in_(request.store_types))

    candidate_stores = query.all()

    results = []

    required_services = set(request.services or [])

    for store in candidate_stores:
        service_names = [service.service_name for service in store.services]

        # services[] uses AND logic:
        # all requested services must exist in this store
        if required_services:
            if not required_services.issubset(set(service_names)):
                continue

        currently_open = is_store_open_now(store)

        if request.open_now is True and not currently_open:
            continue

        distance = calculate_distance_miles(
            search_lat,
            search_lon,
            store.latitude,
            store.longitude,
        )

        if distance > request.radius_miles:
            continue

        results.append(
            {
                "store_id": store.store_id,
                "name": store.name,
                "store_type": store.store_type,
                "status": store.status,
                "latitude": store.latitude,
                "longitude": store.longitude,
                "address_street": store.address_street,
                "address_city": store.address_city,
                "address_state": store.address_state,
                "address_postal_code": store.address_postal_code,
                "address_country": store.address_country,
                "phone": store.phone,
                "services": service_names,
                "hours": {
                    "mon": store.hours_mon,
                    "tue": store.hours_tue,
                    "wed": store.hours_wed,
                    "thu": store.hours_thu,
                    "fri": store.hours_fri,
                    "sat": store.hours_sat,
                    "sun": store.hours_sun,
                },
                "distance_miles": round(distance, 2),
                "is_open_now": currently_open,
            }
        )

    results.sort(key=lambda item: item["distance_miles"])

    response = {
        "searched_location": location,
        "applied_filters": {
            "radius_miles": request.radius_miles,
            "services": request.services or [],
            "store_types": request.store_types or [],
            "open_now": request.open_now,
        },
        "result_count": len(results),
        "results": results,
    }

    set_cache(
        cache_key,
        response,
        settings.SEARCH_CACHE_TTL_SECONDS,
    )

    return response