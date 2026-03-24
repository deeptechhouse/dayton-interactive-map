from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Dayton map ports use area code 937x
    database_url: str = "postgresql+asyncpg://citymap:citymap@localhost:9370/citymap"
    database_url_sync: str = "postgresql://citymap:citymap@localhost:9370/citymap"
    martin_url: str = "http://localhost:9371"
    s3_endpoint_url: str = "http://localhost:9372"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket_name: str = "citymap-tiles"
    s3_region: str = "us-east-1"
    foursquare_api_key: str = ""
    pelias_url: str = "http://localhost:4000"
    app_env: str = "development"
    app_port: int = 9374
    app_host: str = "0.0.0.0"
    cors_origins: str = "http://localhost:9375"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
