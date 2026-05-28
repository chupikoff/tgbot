from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    ADMIN_TG_ID: int
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    TRANSMISSION_HOST: str
    TRANSMISSION_PORT: int = 9091
    TRANSMISSION_USER: str = ""
    TRANSMISSION_PASSWORD: str = ""
    DOWNLOAD_DIR: str = "/home/chpk/media"

    @property
    def database_url(self):
        return f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@postgres:5432/{self.POSTGRES_DB}"

    @property
    def transmission_url(self):
        return f"http://{self.TRANSMISSION_HOST}:{self.TRANSMISSION_PORT}/transmission/rpc"

    class Config:
        env_file = "/home/chpk/tgbot/.env"

settings = Settings()
