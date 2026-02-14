from pydantic import BaseModel


class JwtSettings(BaseModel):
    secret: str = "secret1234"
    algorithm: str = "HS256"
    timeout: int = 15
    refresh_timeout: int = 60
