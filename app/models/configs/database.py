from __future__ import annotations

from typing import Optional

from pydantic import BaseModel


class DatabaseSettings(BaseModel):
    database_url: Optional[str] = None
    type: Optional[str] = None
    user: Optional[str] = None
    password: Optional[str] = None
    name: Optional[str] = None
    host: Optional[str] = None
    port: int = 5432

    def build_url(self, environment: str) -> str:
        if self.database_url:
            return self.database_url

        db_type = (self.type or "").strip().lower()
        if db_type == "sqlite":
            return f"sqlite:///{self.name or f'{environment}.db'}"

        if db_type in ("postgres", "postgresql"):
            required = [self.user, self.password, self.name, self.host]
            if all(required):
                return (
                    f"postgresql+psycopg2://{self.user}:{self.password}"
                    f"@{self.host}:{self.port}/{self.name}"
                )

        if db_type == "mysql":
            required = [self.user, self.password, self.name, self.host]
            if all(required):
                return (
                    f"mysql://{self.user}:{self.password}"
                    f"@{self.host}:{self.port}/{self.name}"
                )

        return f"sqlite:///{environment}.db"
