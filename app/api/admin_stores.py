import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session

from app.core.dependencies import require_roles
from app.db.session import get_db
from app.models.store import Store, StoreService
from app.models.user import User
from app.schemas.admin_store import (
    AdminStoreCreate,
    AdminStorePatch,
    AdminStoreResponse,
    StoreListResponse,
    CSVImportResponse,
)
from app.services.csv_import import import_stores_from_csv
from app.services.geocoding import geocode_address, geocode_postal_code

router = APIRouter(
    prefix="/api/admin/stores",
    tags=["Admin Stores"],
)


def serialize_store(store: Store) -> dict:
    return {
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
        "services": [service.service_name for service in store.services],
        "hours_mon": store.hours_mon,
        "hours_tue": store.hours_tue,
        "hours_wed": store.hours_wed,
        "hours_thu": store.hours_thu,
        "hours_fri": store.hours_fri,
        "hours_sat": store.hours_sat,
        "hours_sun": store.hours_sun,
    }


def resolve_coordinates_for_store_create(
    db: Session,
    request: AdminStoreCreate,
) -> tuple[float, float]:
    """
    Resolve coordinates for store creation.

    If latitude and longitude are provided, use them.
    If both are missing, auto-geocode from full address.
    If only one is missing, reject the request.
    """
    has_lat = request.latitude is not None
    has_lon = request.longitude is not None

    if has_lat and has_lon:
        return request.latitude, request.longitude

    if has_lat != has_lon:
        raise HTTPException(
            status_code=400,
            detail="latitude and longitude must be provided together, or both omitted for auto-geocoding.",
        )

    full_address = (
        f"{request.address_street}, "
        f"{request.address_city}, "
        f"{request.address_state} "
        f"{request.address_postal_code}, "
        f"{request.address_country}"
    )

    try:
        location = geocode_address(db, full_address)
    except ValueError:
        try:
            location = geocode_postal_code(db, request.address_postal_code)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail="Could not auto-geocode store address. Provide latitude and longitude manually.",
            )

    return location["lat"], location["lon"]


@router.get("", response_model=StoreListResponse)
def list_stores(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "marketer", "viewer"])),
):
    total = db.query(Store).count()

    stores = (
        db.query(Store)
        .order_by(Store.store_id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "results": [serialize_store(store) for store in stores],
    }

# Before the "/{store_id}" 
@router.post("/import", response_model=CSVImportResponse)
async def import_stores(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "marketer"])),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are allowed")

    file_content = await file.read()

    result = import_stores_from_csv(db, file_content)

    if not result["success"]:
        raise HTTPException(status_code=400, detail=result)

    return result


@router.get("/{store_id}", response_model=AdminStoreResponse)
def get_store(
    store_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "marketer", "viewer"])),
):
    store = db.query(Store).filter(Store.store_id == store_id).first()

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    return serialize_store(store)


@router.post("", response_model=AdminStoreResponse, status_code=201)
def create_store(
    request: AdminStoreCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "marketer"])),
):
    existing_store = (
        db.query(Store)
        .filter(Store.store_id == request.store_id)
        .first()
    )

    if existing_store:
        raise HTTPException(status_code=400, detail="Store already exists")

    latitude, longitude = resolve_coordinates_for_store_create(db, request)

    store = Store(
        store_id=request.store_id,
        name=request.name,
        store_type=request.store_type,
        status=request.status,
        latitude=latitude,
        longitude=longitude,
        address_street=request.address_street,
        address_city=request.address_city,
        address_state=request.address_state,
        address_postal_code=request.address_postal_code,
        address_country=request.address_country,
        phone=request.phone,
        hours_mon=request.hours_mon,
        hours_tue=request.hours_tue,
        hours_wed=request.hours_wed,
        hours_thu=request.hours_thu,
        hours_fri=request.hours_fri,
        hours_sat=request.hours_sat,
        hours_sun=request.hours_sun,
    )
    
    db.add(store)
    db.flush()

    for service_name in request.services:
        db.add(
            StoreService(
                id=str(uuid.uuid4()),
                store_id=store.store_id,
                service_name=service_name,
            )
        )

    db.commit()
    db.refresh(store)

    return serialize_store(store)


@router.patch("/{store_id}", response_model=AdminStoreResponse)
def patch_store(
    store_id: str,
    request: AdminStorePatch,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "marketer"])),
):
    store = db.query(Store).filter(Store.store_id == store_id).first()

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    update_data = request.model_dump(exclude_unset=True)

    if "name" in update_data:
        store.name = update_data["name"]

    if "phone" in update_data:
        store.phone = update_data["phone"]

    if "status" in update_data:
        store.status = update_data["status"]

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
        if field in update_data:
            setattr(store, field, update_data[field])

    if "services" in update_data:
        db.query(StoreService).filter(
            StoreService.store_id == store.store_id
        ).delete()

        for service_name in update_data["services"]:
            db.add(
                StoreService(
                    id=str(uuid.uuid4()),
                    store_id=store.store_id,
                    service_name=service_name,
                )
            )

    db.commit()
    db.refresh(store)

    return serialize_store(store)


@router.delete("/{store_id}")
def deactivate_store(
    store_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(["admin", "marketer"])),
):
    store = db.query(Store).filter(Store.store_id == store_id).first()

    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    store.status = "inactive"
    db.commit()

    return {
        "message": "Store deactivated successfully",
        "store_id": store_id,
        "status": "inactive",
    }