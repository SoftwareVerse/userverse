from fastapi import APIRouter, Depends, status, Path
from fastapi.responses import JSONResponse

# Models
from app.models.generic_pagination import PaginatedResponse
from app.models.generic_response import GenericResponseModel
from app.models.company.roles import (
    RoleCreateModel,
    RoleDeleteModel,
    RoleQueryParamsModel,
    RoleReadModel,
    RoleUpdateModel,
)
from app.models.app_error import AppErrorResponseModel
from app.models.company.response_messages import (
    CompanyRoleResponseMessages,
)

# Auth
from app.models.tags import UserverseApiTag
from app.dependencies.common import CommonJWTRouteDependencies

# Business Logic
from app.logic.company.role import RoleService
from app.utils.shared_context import SharedContext

# Utilities
from app.utils.app_error import AppError

router = APIRouter()
tag = UserverseApiTag.COMPANY_ROLE_MANAGEMENT.name


@router.post(
    "/company/{company_id}/role",
    tags=[tag],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": GenericResponseModel[RoleReadModel]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def create_role_api(
    payload: RoleCreateModel,
    company_id: int = Path(..., description="The unique identifier of the company"),
    common: CommonJWTRouteDependencies = Depends(),
):
    """
    Create a new role for the specified company.

    - **Requires**: Authenticated user
    - **Returns**: The created role
    """
    try:
        service = RoleService(
            SharedContext(user=common.user, db_session=common.session)
        )
        response = service.create_role(payload=payload, company_id=company_id)
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
        201: {"model": GenericResponseModel[RoleReadModel]},
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def update_role_api(
    payload: RoleUpdateModel,
    company_id: int = Path(..., description="The company ID associated with the role"),
    name: str = Path(..., description="The name of the role to update"),
    common: CommonJWTRouteDependencies = Depends(),
):
    """
    Update a role's description by its name.

    - **Requires**: Authenticated user
    - **Returns**: Updated role data
    """
    try:
        service = RoleService(
            SharedContext(user=common.user, db_session=common.session)
        )
        response = service.update_role(
            company_id=company_id, name=name, payload=payload
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
    payload: RoleDeleteModel,
    company_id: int = Path(..., description="Company ID to delete role from"),
    common: CommonJWTRouteDependencies = Depends(),
):
    """
    Delete a role from a company and reassign affected users to a replacement role.

    - **Requires**: Authenticated user
    - **Returns**: Success message with result info
    """
    try:
        service = RoleService(
            SharedContext(user=common.user, db_session=common.session)
        )
        response = service.delete_role(payload=payload, company_id=company_id)
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
        200: {"model": GenericResponseModel[PaginatedResponse[RoleReadModel]]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def get_company_roles_api(
    company_id: int = Path(..., description="ID of the company whose roles to fetch"),
    query_params: RoleQueryParamsModel = Depends(),
    common: CommonJWTRouteDependencies = Depends(),
):
    """
    Get a paginated list of all roles associated with a specific company.

    - **Supports**: Filtering, pagination
    - **Requires**: Authenticated user
    """
    try:
        service = RoleService(
            SharedContext(user=common.user, db_session=common.session)
        )
        response = service.get_company_roles(
            payload=query_params, company_id=company_id
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=GenericResponseModel(
                message=CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value,
                data=response.model_dump(),
            ).model_dump(),
        )
    except (AppError, Exception) as e:
        raise e
