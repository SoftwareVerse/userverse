from typing import Optional

from pydantic import BaseModel


class EmailSettings(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None

    # Match your JSON keys (EMAIL_TLS / EMAIL_SSL)
    email_tls: Optional[bool] = None
    email_ssl: Optional[bool] = None
