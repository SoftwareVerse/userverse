from __future__ import annotations

from typing import Optional

from pydantic import BaseModel

from app.models.configs.cors import CorsSettings
from app.models.configs.email import EmailSettings
from app.models.configs.jwt import JwtSettings


class RuntimeSettings(BaseModel):
    environment: str
    database_url: str
    server_url: str
    cor_origins: CorsSettings
    jwt: JwtSettings
    email: EmailSettings
    name: str
    version: str
    description: str
    repository: Optional[str] = None
    documentation: Optional[str] = None
