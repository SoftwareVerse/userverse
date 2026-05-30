# app/models/generic_pagination.py
from typing import Any, Generic, Iterable, List, TypeVar
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


class PaginationMeta(BaseModel):
    total_records: int
    limit: int
    current_page: int
    total_pages: int


class PaginatedResponse(BaseModel, Generic[T]):
    records: List[T]
    pagination: PaginationMeta


def get_page_offset(*, page: int, limit: int) -> int:
    return (page - 1) * limit


def get_total_pages(*, total_records: int, limit: int) -> int:
    return (total_records + limit - 1) // limit


def build_pagination_meta(
    *, total_records: int, limit: int, page: int
) -> PaginationMeta:
    return PaginationMeta(
        total_records=total_records,
        limit=limit,
        current_page=page,
        total_pages=get_total_pages(total_records=total_records, limit=limit),
    )


def apply_pagination(query: Any, *, page: int, limit: int, order_by: Iterable[Any]):
    return (
        query.order_by(*order_by)
        .offset(get_page_offset(page=page, limit=limit))
        .limit(limit)
    )
