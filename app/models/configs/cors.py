from pydantic import BaseModel, Field


class CorsSettings(BaseModel):
    allowed: list[str] = Field(default_factory=lambda: ["*"])
    blocked: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])
