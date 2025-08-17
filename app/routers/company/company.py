from fastapi import APIRouter, Depends, status, Query, Path
from fastapi.responses import JSONResponse

# Models
from app.models.company.user import CompanyUserRead
from app.models.generic_pagination import PaginatedResponse
from app.models.generic_response import GenericResponseModel
from app.models.company.company import CompanyCreate, CompanyRead, CompanyUpdate
from app.models.app_error import AppErrorResponseModel
from app.models.company.response_messages import (
    CompanyResponseMessages,
    CompanyUserResponseMessages,
)

# Auth
from app.models.tags import UserverseApiTag
from app.security.jwt import get_current_user_from_jwt_token
from app.models.user.user import UserQueryParams, UserReadModel

# Logic
from app.logic.company.company import CompanyService
from app.logic.company.user import CompanyUserService

# Utils
from app.utils.app_error import AppError

router = APIRouter()
tag = UserverseApiTag.COMPANY_MANAGEMENT.name


@router.post(
    "/company",
    tags=[tag],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": GenericResponseModel[CompanyRead]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def create_company_api(
    payload: CompanyCreate,
    user: UserReadModel = Depends(get_current_user_from_jwt_token),
):
    """
    Create a new company and initialize default roles.

    - **Stores**: Address in `primary_meta_data`
    - **Creates**: Administrator and Viewer roles by default
    - **Requires**: Authenticated user
    - **Returns**: Created company data
    """
    try:
        response = CompanyService().create_company(payload, created_by=user)
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=GenericResponseModel(
                message=CompanyResponseMessages.COMPANY_CREATED.value,
                data=response.model_dump(),
            ).model_dump(),
        )
    except (AppError, Exception) as e:
        raise e


@router.get(
    "/company",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[CompanyRead]},
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def get_company_api(
    email: str = Query(None, description="(Optional) Company email address"),
    company_id: int = Query(None, description="(Optional) Company ID"),
    user: UserReadModel = Depends(get_current_user_from_jwt_token),
):
    """
    Retrieve a company by email or company ID.

    - **Priority**: email > company_id
    - **Requires**: Authenticated user
    - **Returns**: Company data if found
    """
    try:
        if email:
            company = CompanyService().get_company(user=user, email=email)
        elif company_id:
            company = CompanyService().get_company(user=user, company_id=company_id)
        else:
            raise AppError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=CompanyResponseMessages.COMPANY_ID_OR_EMAIL_REQUIRED.value,
            )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=GenericResponseModel(
                message=CompanyResponseMessages.COMPANY_FOUND.value,
                data=company.model_dump(),
            ).model_dump(),
        )
    except (AppError, Exception) as e:
        raise e


@router.patch(
    "/company/{company_id}",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[CompanyRead]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def update_company_api(
    company_updates: CompanyUpdate,
    company_id: int = Path(..., description="ID of the company to update"),
    user: UserReadModel = Depends(get_current_user_from_jwt_token),
):
    """
    Update company details by its ID.

    - **Requires**: User must be an administrator
    - **Returns**: Updated company data
    """
    try:
        response = CompanyService().update_company(
            payload=company_updates,
            company_id=company_id,
            user=user,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=GenericResponseModel(
                message=CompanyResponseMessages.COMPANY_UPDATED.value,
                data=response.model_dump(),
            ).model_dump(),
        )
    except (AppError, Exception) as e:
        raise e


@router.get(
    "/company/{company_id}/users",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[PaginatedResponse[CompanyUserRead]]},
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def get_company_users_api(
    company_id: int = Path(..., description="Company ID"),
    params: UserQueryParams = Depends(),
    user: UserReadModel = Depends(get_current_user_from_jwt_token),
):
    """
    Get paginated list of users belonging to a company.

    - **Supports**: Filtering, pagination
    - **Requires**: Authenticated user
    - **Returns**: List of company users
    """
    try:
        response = CompanyUserService().get_company_user(
            company_id=company_id,
            params=params,
            user=user,
        )
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=GenericResponseModel(
                message=CompanyUserResponseMessages.GET_COMPANY_USERS.value,
                data=response.model_dump(),
            ).model_dump(),
        )
    except (AppError, Exception) as e:
        raise e
