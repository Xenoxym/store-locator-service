from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    DATABASE_URL: str

    JWT_SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    REDIS_URL: str = "redis://localhost:6379/0"

    GEOCODING_CACHE_TTL_SECONDS: int = 60 * 60 * 24 * 30
    SEARCH_CACHE_TTL_SECONDS: int = 60 * 10

    RATE_LIMIT_PER_MINUTE: int = 10
    RATE_LIMIT_PER_HOUR: int = 100

    US_CENSUS_GEOCODER_URL: str = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress"
    US_CENSUS_BENCHMARK: str = "Public_AR_Current"
    ZIPPOPOTAMUS_URL: str = "https://api.zippopotam.us/us"

    class Config:
        env_file = ".env"


settings = Settings()