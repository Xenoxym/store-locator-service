import csv
import io
import uuid
from typing import Any

from sqlalchemy.orm import Session

from app.models.store import Store, StoreService
from app.services.geocoding import geocode_address, geocode_postal_code


EXPECTED_HEADERS = [
    "store_id",
    "name",
    "store_type",
    "status",
    "address_street",
    "address_city",
    "address_state",
    "address_postal_code",
    "address_country",
    "phone",
    "services",
    "hours_mon",
    "hours_tue",
    "hours_wed",
    "hours_thu",
    "hours_fri",
    "hours_sat",
    "hours_sun",
]


VALID_STORE_TYPES = {"flagship", "regular", "outlet", "express"}
VALID_STATUSES = {"active", "inactive", "temporarily_closed"}
VALID_SERVICES = {
    "pharmacy",
    "pickup",
    "returns",
    "optical",
    "photo_printing",
    "gift_wrapping",
    "automotive",
    "garden_center",
}


REQUIRED_HEADERS = [
    "store_id",
    "name",
    "store_type",
    "status",
    "address_street",
    "address_city",
    "address_state",
    "address_postal_code",
    "address_country",
    "phone",
    "services",
    "hours_mon",
    "hours_tue",
    "hours_wed",
    "hours_thu",
    "hours_fri",
    "hours_sat",
    "hours_sun",
]


OPTIONAL_HEADERS = [
    "latitude",
    "longitude",
]


ALLOWED_HEADERS = REQUIRED_HEADERS + OPTIONAL_HEADERS


def validate_headers(headers: list[str] | None) -> None:
    if headers is None:
        raise ValueError("CSV file has no headers")

    missing_required = [header for header in REQUIRED_HEADERS if header not in headers]
    unknown_headers = [header for header in headers if header not in ALLOWED_HEADERS]

    has_lat = "latitude" in headers
    has_lon = "longitude" in headers

    if has_lat != has_lon:
        raise ValueError(
            "CSV must include both latitude and longitude columns, or omit both for auto-geocoding"
        )

    if missing_required:
        raise ValueError(f"Missing required CSV headers: {missing_required}")

    if unknown_headers:
        raise ValueError(f"Unknown CSV headers: {unknown_headers}")


def is_valid_open_time(hour: int, minute: int) -> bool:
    return 0 <= hour <= 23 and 0 <= minute <= 59


def is_valid_close_time(hour: int, minute: int) -> bool:
    if hour == 24:
        return minute == 0
    return 0 <= hour <= 23 and 0 <= minute <= 59


def validate_hours(value: str, field_name: str) -> None:
    if value == "closed":
        return

    if "-" not in value:
        raise ValueError(f"{field_name} must be HH:MM-HH:MM or closed")

    open_time, close_time = value.split("-", 1)

    if len(open_time) != 5 or len(close_time) != 5:
        raise ValueError(f"{field_name} must be HH:MM-HH:MM or closed")

    try:
        open_hour, open_minute = map(int, open_time.split(":"))
        close_hour, close_minute = map(int, close_time.split(":"))
    except ValueError:
        raise ValueError(f"{field_name} must contain numeric time values")

    if not is_valid_open_time(open_hour, open_minute):
        raise ValueError(f"{field_name} open time must be between 00:00 and 23:59")

    if not is_valid_close_time(close_hour, close_minute):
        raise ValueError(f"{field_name} close time must be between 00:00 and 24:00")

    if (open_hour, open_minute) >= (close_hour, close_minute):
        raise ValueError(f"{field_name} open time must be earlier than close time")


def validate_row(row: dict[str, str], row_number: int) -> None:
    errors = []

    required_fields = [
        "store_id",
        "name",
        "store_type",
        "status",
        "address_street",
        "address_city",
        "address_state",
        "address_postal_code",
        "address_country",
        "phone",
    ]

    for field in required_fields:
        if not row.get(field):
            errors.append(f"{field} is required")

    if row.get("store_type") and row["store_type"] not in VALID_STORE_TYPES:
        errors.append(f"invalid store_type: {row['store_type']}")

    if row.get("status") and row["status"] not in VALID_STATUSES:
        errors.append(f"invalid status: {row['status']}")

    latitude_value = row.get("latitude", "")
    longitude_value = row.get("longitude", "")

    has_lat = bool(latitude_value)
    has_lon = bool(longitude_value)

    if has_lat != has_lon:
        errors.append(
            "latitude and longitude must be provided together, or both omitted for auto-geocoding"
        )

    if has_lat and has_lon:
        try:
            latitude = float(latitude_value)
            if not (-90 <= latitude <= 90):
                errors.append("latitude must be between -90 and 90")
        except Exception:
            errors.append("latitude must be a valid number")

        try:
            longitude = float(longitude_value)
            if not (-180 <= longitude <= 180):
                errors.append("longitude must be between -180 and 180")
        except Exception:
            errors.append("longitude must be a valid number")

    if row.get("address_state") and len(row["address_state"]) != 2:
        errors.append("address_state must be 2 characters")

    if row.get("address_postal_code") and len(row["address_postal_code"]) != 5:
        errors.append("address_postal_code must be 5 digits")

    services = row.get("services", "")
    if services:
        for service in services.split("|"):
            if service not in VALID_SERVICES:
                errors.append(f"invalid service: {service}")

    hour_fields = [
        "hours_mon",
        "hours_tue",
        "hours_wed",
        "hours_thu",
        "hours_fri",
        "hours_sat",
        "hours_sun",
    ]

    for field in hour_fields:
        value = row.get(field)
        if not value:
            errors.append(f"{field} is required")
        else:
            try:
                validate_hours(value, field)
            except ValueError as e:
                errors.append(str(e))

    if errors:
        raise ValueError(f"Row {row_number}: " + "; ".join(errors))


def resolve_coordinates_for_csv_row(db: Session, row: dict[str, str]) -> tuple[float, float]:
    """
    Resolve coordinates for one CSV row.

    If latitude/longitude are present, use them.
    If both are missing, auto-geocode from address.
    """
    latitude_value = row.get("latitude", "")
    longitude_value = row.get("longitude", "")

    if latitude_value and longitude_value:
        return float(latitude_value), float(longitude_value)

    full_address = (
        f"{row['address_street']}, "
        f"{row['address_city']}, "
        f"{row['address_state']} "
        f"{row['address_postal_code']}, "
        f"{row['address_country']}"
    )

    try:
        result = geocode_address(db, full_address)
    except ValueError:
        result = geocode_postal_code(db, row["address_postal_code"])

    return result["lat"], result["lon"]


def upsert_store(db: Session, row: dict[str, str]) -> str:
    existing_store = (
        db.query(Store)
        .filter(Store.store_id == row["store_id"])
        .first()
    )

    if existing_store:
        store = existing_store
        action = "updated"
    else:
        store = Store(store_id=row["store_id"])
        db.add(store)
        action = "created"

    store.name = row["name"]
    store.store_type = row["store_type"]
    store.status = row["status"]

    latitude, longitude = resolve_coordinates_for_csv_row(db, row)
    store.latitude = latitude
    store.longitude = longitude

    store.address_street = row["address_street"]
    store.address_city = row["address_city"]
    store.address_state = row["address_state"]
    store.address_postal_code = row["address_postal_code"]
    store.address_country = row["address_country"]

    store.phone = row["phone"]

    store.hours_mon = row["hours_mon"]
    store.hours_tue = row["hours_tue"]
    store.hours_wed = row["hours_wed"]
    store.hours_thu = row["hours_thu"]
    store.hours_fri = row["hours_fri"]
    store.hours_sat = row["hours_sat"]
    store.hours_sun = row["hours_sun"]

    db.flush()

    db.query(StoreService).filter(
        StoreService.store_id == row["store_id"]
    ).delete()

    services = row["services"].split("|") if row.get("services") else []

    for service_name in services:
        db.add(
            StoreService(
                id=str(uuid.uuid4()),
                store_id=row["store_id"],
                service_name=service_name,
            )
        )

    return action


def import_stores_from_csv(db: Session, file_content: bytes) -> dict[str, Any]:
    decoded = file_content.decode("utf-8-sig")
    csv_file = io.StringIO(decoded)

    reader = csv.DictReader(csv_file)

    total_rows = 0
    created_count = 0
    updated_count = 0
    failed_count = 0
    row_errors = []

    try:
        validate_headers(reader.fieldnames)

        rows = list(reader)
        total_rows = len(rows)

        for row_number, row in enumerate(rows, start=2):
            try:
                validate_row(row, row_number)
                action = upsert_store(db, row)

                if action == "created":
                    created_count += 1
                elif action == "updated":
                    updated_count += 1

            except Exception as e:
                failed_count += 1
                row_errors.append(
                    {
                        "row_number": row_number,
                        "error": str(e),
                    }
                )
                raise

        db.commit()

    except Exception as e:
        db.rollback()

        if not row_errors:
            row_errors.append(
                {
                    "row_number": None,
                    "error": str(e),
                }
            )
            failed_count = 1

        return {
            "success": False,
            "message": "CSV import failed. Transaction rolled back.",
            "total_rows_processed": total_rows,
            "created": 0,
            "updated": 0,
            "failed": failed_count,
            "errors": row_errors,
        }

    return {
        "success": True,
        "message": "CSV import completed successfully.",
        "total_rows_processed": total_rows,
        "created": created_count,
        "updated": updated_count,
        "failed": failed_count,
        "errors": row_errors,
    }