from fastapi import APIRouter, Depends, status, Query, Path
from fastapi.responses import JSONResponse

# Models
from app.models.generic_pagination import PaginatedResponse
from app.models.generic_response import GenericResponseModel
from app.models.company.roles import (
    RoleCreate,
    RoleDelete,
    RoleQueryParams,
    RoleRead,
    RoleUpdate,
)
from app.models.app_error import AppErrorResponseModel
from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyRoleResponseMessages,
)

# Auth
from app.models.tags import UserverseApiTag
from app.security.jwt import get_current_user_from_jwt_token
from app.models.user.user import UserRead

# Business Logic
from app.logic.company.role import RoleService

# Utilities
from app.utils.app_error import AppError

router = APIRouter()
tag = UserverseApiTag.COMPANY_ROLE_MANAGEMENT.name


@router.post(
    "/company/{company_id}/role",
    tags=[tag],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": GenericResponseModel[RoleRead]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def create_role_api(
    payload: RoleCreate,
    company_id: int = Path(..., description="The unique identifier of the company"),
    user: UserRead = Depends(get_current_user_from_jwt_token),
):
    """
    Create a new role for the specified company.

    - **Requires**: Authenticated user
    - **Returns**: The created role
    """
    try:
        role_service = RoleService()
        response = role_service.create_role(
            payload=payload, created_by=user, company_id=company_id
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": CompanyRoleResponseMessages.ROLE_CREATION_SUCCESS.value,
                "data": response.model_dump(),
            },
        )
    except (AppError, Exception) as e:
        raise e


@router.patch(
    "/company/{company_id}/role/{name}",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        201: {"model": GenericResponseModel[RoleRead]},
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def update_role_api(
    payload: RoleUpdate,
    company_id: int = Path(..., description="The company ID associated with the role"),
    name: str = Path(..., description="The name of the role to update"),
    user: UserRead = Depends(get_current_user_from_jwt_token),
):
    """
    Update a role's description by its name.

    - **Requires**: Authenticated user
    - **Returns**: Updated role data
    """
    try:
        role_service = RoleService()
        response = role_service.update_role(
            updated_by=user, company_id=company_id, name=name, payload=payload
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": CompanyRoleResponseMessages.ROLE_UPDATED.value,
                "data": response.model_dump(),
            },
        )
    except (AppError, Exception) as e:
        raise e


@router.delete(
    "/company/{company_id}/role",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        201: {"model": GenericResponseModel[dict]},
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def delete_role_api(
    payload: RoleDelete,
    company_id: int = Path(..., description="Company ID to delete role from"),
    user: UserRead = Depends(get_current_user_from_jwt_token),
):
    """
    Delete a role from a company and reassign affected users to a replacement role.

    - **Requires**: Authenticated user
    - **Returns**: Success message with result info
    """
    try:
        response = RoleService.delete_role(
            payload=payload, deleted_by=user, company_id=company_id
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": CompanyRoleResponseMessages.ROLE_DELETED.value,
                "data": response,
            },
        )
    except (AppError, Exception) as e:
        raise e


@router.get(
    "/company/{company_id}/roles",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[PaginatedResponse[RoleRead]]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def get_company_roles_api(
    company_id: int = Path(..., description="ID of the company whose roles to fetch"),
    query_params: RoleQueryParams = Depends(),
    user: UserRead = Depends(get_current_user_from_jwt_token),
):
    """
    Get a paginated list of all roles associated with a specific company.

    - **Supports**: Filtering, pagination
    - **Requires**: Authenticated user
    """
    try:
        response = RoleService.get_company_roles(
            payload=query_params, company_id=company_id, user=user
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=GenericResponseModel(
                message=CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value,
                data=response,
            ).model_dump(),
        )
    except (AppError, Exception) as e:
        raise e
