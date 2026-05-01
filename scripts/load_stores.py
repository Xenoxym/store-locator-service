import csv
import sys
import uuid
from pathlib import Path

from app.db.session import SessionLocal
from app.models.store import Store, StoreService


EXPECTED_HEADERS = [
    "store_id",
    "name",
    "store_type",
    "status",
    "latitude",
    "longitude",
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


def validate_headers(headers):
    if headers != EXPECTED_HEADERS:
        raise ValueError(
            f"Invalid CSV headers.\nExpected: {EXPECTED_HEADERS}\nGot: {headers}"
        )


def validate_row(row, row_number):
    errors = []

    if not row["store_id"].startswith("S"):
        errors.append("store_id must start with S")

    if row["store_type"] not in VALID_STORE_TYPES:
        errors.append(f"invalid store_type: {row['store_type']}")

    if row["status"] not in VALID_STATUSES:
        errors.append(f"invalid status: {row['status']}")

    try:
        lat = float(row["latitude"])
        lon = float(row["longitude"])

        if not (-90 <= lat <= 90):
            errors.append("latitude out of range")
        if not (-180 <= lon <= 180):
            errors.append("longitude out of range")
    except ValueError:
        errors.append("latitude/longitude must be numbers")

    services = row["services"].split("|") if row["services"] else []
    for service in services:
        if service not in VALID_SERVICES:
            errors.append(f"invalid service: {service}")

    if errors:
        raise ValueError(f"Row {row_number}: " + "; ".join(errors))


def load_stores(csv_path: str):
    path = Path(csv_path)

    if not path.exists():
        raise FileNotFoundError(f"CSV file not found: {csv_path}")

    db = SessionLocal()

    created = 0
    updated = 0
    failed = 0
    errors = []

    try:
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            reader = csv.DictReader(file)

            validate_headers(reader.fieldnames)

            for row_number, row in enumerate(reader, start=2):
                try:
                    validate_row(row, row_number)

                    existing_store = (
                        db.query(Store)
                        .filter(Store.store_id == row["store_id"])
                        .first()
                    )

                    if existing_store:
                        store = existing_store
                        updated += 1
                    else:
                        store = Store(store_id=row["store_id"])
                        db.add(store)
                        created += 1

                    store.name = row["name"]
                    store.store_type = row["store_type"]
                    store.status = row["status"]
                    store.latitude = float(row["latitude"])
                    store.longitude = float(row["longitude"])
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

                    services = row["services"].split("|") if row["services"] else []

                    for service in services:
                        db.add(
                            StoreService(
                                id=str(uuid.uuid4()),
                                store_id=row["store_id"],
                                service_name=service,
                            )
                        )

                except Exception as e:
                    failed += 1
                    errors.append(str(e))
                    raise

        db.commit()

        print("CSV import completed.")
        print(f"File: {csv_path}")
        print(f"Created: {created}")
        print(f"Updated: {updated}")
        print(f"Failed: {failed}")

    except Exception:
        db.rollback()
        print("CSV import failed. Transaction rolled back.")
        for error in errors:
            print(error)
        raise

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python scripts/load_stores.py data/stores_50.csv")
        sys.exit(1)

    load_stores(sys.argv[1])