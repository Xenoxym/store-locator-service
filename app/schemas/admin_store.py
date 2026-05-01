from typing import Any, List, Optional
from pydantic import BaseModel, Field, ConfigDict


VALID_STORE_TYPES = {"flagship", "regular", "outlet", "express"}
VALID_STATUSES = {"active", "inactive", "temporarily_closed"}


class AdminStoreCreate(BaseModel):
    store_id: str
    name: str
    store_type: str
    status: str = "active"

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)

    address_street: str
    address_city: str
    address_state: str
    address_postal_code: str
    address_country: str = "USA"

    phone: str
    services: List[str]

    hours_mon: str
    hours_tue: str
    hours_wed: str
    hours_thu: str
    hours_fri: str
    hours_sat: str
    hours_sun: str


class AdminStoreResponse(BaseModel):
    store_id: str
    name: str
    store_type: str
    status: str

    latitude: float
    longitude: float

    address_street: str
    address_city: str
    address_state: str
    address_postal_code: str
    address_country: str

    phone: str
    services: List[str]

    hours_mon: str
    hours_tue: str
    hours_wed: str
    hours_thu: str
    hours_fri: str
    hours_sat: str
    hours_sun: str


class StoreListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    results: List[AdminStoreResponse]


class AdminStorePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = None
    phone: Optional[str] = None
    services: Optional[List[str]] = None
    status: Optional[str] = None

    hours_mon: Optional[str] = None
    hours_tue: Optional[str] = None
    hours_wed: Optional[str] = None
    hours_thu: Optional[str] = None
    hours_fri: Optional[str] = None
    hours_sat: Optional[str] = None
    hours_sun: Optional[str] = None


class CSVImportResponse(BaseModel):
    success: bool
    message: str
    total_rows_processed: int
    created: int
    updated: int
    failed: int
    errors: list[dict[str, Any]]