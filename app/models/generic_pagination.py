# app/models/generic_pagination.py
from typing import Generic, List, TypeVar
from pydantic import BaseModel, Field
from enum import Enum


T = TypeVar("T")


class MatchType(str, Enum):
    PARTIAL = "partial"
    EXACT = "exact"
    STARTS_WITH = "starts_with"


class FilterLogic(str, Enum):
    OR = "or"
    AND = "and"


class PaginationParams(BaseModel):
    limit: int = Field(10, ge=1, le=100)
    page: int = Field(1, ge=1)  # Page is 1-indexed

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.limit


class PaginationMeta(BaseModel):
    total_records: int
    limit: int
    current_page: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    records: List[T]
    pagination: PaginationMeta
