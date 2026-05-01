from app.services.distance import calculate_bounding_box, calculate_distance_miles


def test_calculate_bounding_box_contains_center():
    box = calculate_bounding_box(
        lat=40.7128,
        lon=-74.0060,
        radius_miles=10,
    )

    assert box["min_lat"] < 40.7128 < box["max_lat"]
    assert box["min_lon"] < -74.0060 < box["max_lon"]


def test_calculate_bounding_box_has_valid_range():
    box = calculate_bounding_box(
        lat=40.7128,
        lon=-74.0060,
        radius_miles=10,
    )

    assert box["min_lat"] < box["max_lat"]
    assert box["min_lon"] < box["max_lon"]


def test_calculate_distance_miles_same_point_is_zero_or_near_zero():
    distance = calculate_distance_miles(
        40.7128,
        -74.0060,
        40.7128,
        -74.0060,
    )

    assert distance < 0.01


def test_calculate_distance_miles_between_nyc_and_boston():
    distance = calculate_distance_miles(
        40.7128,
        -74.0060,
        42.3601,
        -71.0589,
    )

    assert 180 <= distance <= 230