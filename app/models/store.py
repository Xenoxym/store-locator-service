from sqlalchemy import (
    Column,
    String,
    Float,
    DateTime,
    ForeignKey,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.base import Base


class Store(Base):
    __tablename__ = "stores"

    store_id = Column(String(10), primary_key=True, index=True)

    name = Column(String(255), nullable=False)
    store_type = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="active")

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    address_street = Column(String(255), nullable=False)
    address_city = Column(String(100), nullable=False)
    address_state = Column(String(2), nullable=False)
    address_postal_code = Column(String(5), nullable=False)
    address_country = Column(String(3), nullable=False, default="USA")

    phone = Column(String(20), nullable=False)

    hours_mon = Column(String(20), nullable=False)
    hours_tue = Column(String(20), nullable=False)
    hours_wed = Column(String(20), nullable=False)
    hours_thu = Column(String(20), nullable=False)
    hours_fri = Column(String(20), nullable=False)
    hours_sat = Column(String(20), nullable=False)
    hours_sun = Column(String(20), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    services = relationship(
        "StoreService",
        back_populates="store",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_stores_lat_lon", "latitude", "longitude"),
        Index("idx_stores_status", "status"),
        Index("idx_stores_store_type", "store_type"),
        Index("idx_stores_postal_code", "address_postal_code"),
    )


class StoreService(Base):
    __tablename__ = "store_services"

    id = Column(String(50), primary_key=True)
    store_id = Column(String(10), ForeignKey("stores.store_id"), nullable=False)
    service_name = Column(String(50), nullable=False)

    store = relationship("Store", back_populates="services")

    __table_args__ = (
        Index("idx_store_services_store_id", "store_id"),
        Index("idx_store_services_service_name", "service_name"),
    )