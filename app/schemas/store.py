from typing import List, Optional
from pydantic import BaseModel, Field, model_validator


class StoreSearchRequest(BaseModel):
    address: Optional[str] = None
    postal_code: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None

    radius_miles: float = Field(default=10, gt=0, le=100)

    services: Optional[List[str]] = None
    store_types: Optional[List[str]] = None
    open_now: Optional[bool] = None

    @model_validator(mode="after")
    def validate_search_input(self):
        has_address = self.address is not None
        has_postal_code = self.postal_code is not None
        has_coordinates = self.latitude is not None and self.longitude is not None

        input_count = sum([has_address, has_postal_code, has_coordinates])

        if input_count != 1:
            raise ValueError(
                "Provide exactly one search input: address, postal_code, or latitude/longitude."
            )

        if self.latitude is not None:
            if not (-90 <= self.latitude <= 90):
                raise ValueError("latitude must be between -90 and 90.")

        if self.longitude is not None:
            if not (-180 <= self.longitude <= 180):
                raise ValueError("longitude must be between -180 and 180.")

        return self


class StoreResult(BaseModel):
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

    hours: dict

    distance_miles: float
    is_open_now: bool


class StoreSearchResponse(BaseModel):
    searched_location: dict
    applied_filters: dict
    result_count: int
    results: List[StoreResult]