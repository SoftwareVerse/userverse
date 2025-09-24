"""Pydantic models describing job payloads."""

from __future__ import annotations

from typing import Any, Dict, Literal

from pydantic import BaseModel, EmailStr, Field


class EmailJob(BaseModel):
    to: EmailStr
    reason: str
    context: Dict[str, Any] = Field(default_factory=dict)


class NotifyEmail(BaseModel):
    type: Literal["email"]
    to: EmailStr
    reason: str
    context: Dict[str, Any] = Field(default_factory=dict)
