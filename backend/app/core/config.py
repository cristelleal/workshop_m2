from pydantic import field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    cors_origins: str = ""
    log_level: str = "INFO"

    @field_validator("database_url")
    @classmethod
    def force_psycopg_driver(cls, v: str) -> str:
        # Accepte postgresql:// (compose de la VM) et force le driver psycopg 3
        for prefix in ("postgresql://", "postgres://"):
            if v.startswith(prefix):
                return "postgresql+psycopg://" + v.removeprefix(prefix)
        return v

    @field_validator("jwt_secret_key")
    @classmethod
    def check_jwt_secret_strength(cls, v: str) -> str:
        # Clé vide : chaque /auth/login renverrait une 500. Clé courte : tokens forgeables par force brute.
        # On préfère refuser de démarrer avec un message clair.
        if len(v) < 32:
            raise ValueError(
                "JWT_SECRET_KEY doit faire au moins 32 caractères "
                "(à générer avec : openssl rand -base64 48)"
            )
        return v

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()