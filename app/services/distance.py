import math
from geopy.distance import geodesic


def calculate_bounding_box(lat: float, lon: float, radius_miles: float) -> dict:
    """
    Calculate latitude/longitude bounding box for a given center point and radius.

    This is used as the SQL pre-filter before exact distance calculation.
    """
    latitude_delta = radius_miles / 69.0

    latitude_radians = math.radians(lat)
    longitude_delta = radius_miles / (69.0 * math.cos(latitude_radians))

    return {
        "min_lat": lat - latitude_delta,
        "max_lat": lat + latitude_delta,
        "min_lon": lon - longitude_delta,
        "max_lon": lon + longitude_delta,
    }


def calculate_distance_miles(
    search_lat: float,
    search_lon: float,
    store_lat: float,
    store_lon: float,
) -> float:
    """
    Calculate exact distance in miles using geopy.
    """
    return geodesic(
        (search_lat, search_lon),
        (store_lat, store_lon),
    ).miles