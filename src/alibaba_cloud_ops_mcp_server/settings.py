from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    headers_credential_only: bool = False
    env: str = "domestic"


settings = Settings()
