from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_TG_ID: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    TRANSMISSION_HOST: str = ""
    TRANSMISSION_PORT: int = 9091
    TRANSMISSION_USER: str = ""
    TRANSMISSION_PASSWORD: str = ""
    DOWNLOAD_DIR: str = "/home/chpk/media"
    SERVICE_API_TOKEN: str = ""
    SERVICE_API_URL: str = "http://192.168.88.2:7777"
    OMDB_API_KEY: str = ""
    MEDIA_DIR: str = "/home/chpk/media"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:"
            f"{self.POSTGRES_PASSWORD}@postgres:5432/{self.POSTGRES_DB}"
        )

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
