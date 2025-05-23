from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

# Tags & Models
from app.models.tags import UserverseApiTag
from app.models.user.response_messages import UserResponseMessages
from app.models.user.user import (
    TokenResponseModel,
    UserLogin,
    UserCreate,
    UserRead,
    UserUpdate,
)
from app.models.company.company import CompanyQueryParams, CompanyRead
from app.models.company.response_messages import (
    CompanyUserResponseMessages,
    CompanyResponseMessages,
)
from app.models.generic_response import GenericResponseModel
from app.models.generic_pagination import PaginatedResponse
from app.models.app_error import AppErrorResponseModel

# Security & Utils
from app.security.basic_auth import get_basic_auth_credentials
from app.security.jwt import get_current_user_from_jwt_token
from app.utils.app_error import AppError

# Logic
from app.logic.user.user import UserService

router = APIRouter()
tag = UserverseApiTag.USER_MANAGEMENT.name


@router.patch(
    "/user/login",
    tags=[tag],
    status_code=status.HTTP_202_ACCEPTED,
    responses={
        202: {"model": TokenResponseModel},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def user_login_api(
    credentials: UserLogin = Depends(get_basic_auth_credentials),
):
    """
    Authenticate user using basic auth credentials.

    - **Returns**: Access token for future authenticated requests
    """
    try:
        response = UserService().user_login(user_credentials=credentials)
        return JSONResponse(
            status_code=status.HTTP_202_ACCEPTED,
            content={
                "message": UserResponseMessages.USER_LOGGED_IN.value,
                "data": response.model_dump(),
            },
        )
    except (AppError, Exception) as e:
        raise e


@router.post(
    "/user",
    tags=[tag],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": GenericResponseModel[UserRead]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def create_user_api(
    user: UserCreate,
    credentials: UserLogin = Depends(get_basic_auth_credentials),
):
    """
    Create a new user account.

    - **Requires**: Valid basic auth credentials
    - **Returns**: Created user details
    """
    try:
        response = UserService().create_user(
            user_credentials=credentials,
            user_data=user,
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": UserResponseMessages.USER_CREATED.value,
                "data": response.model_dump(),
            },
        )
    except (AppError, Exception) as e:
        raise e


@router.get(
    "/user",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[UserRead]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def get_user_api(
    user: UserRead = Depends(get_current_user_from_jwt_token),
):
    """
    Retrieve current authenticated user's details.
    """
    try:
        response = UserService().get_user(user_email=user.email)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "message": UserResponseMessages.USER_FOUND.value,
                "data": response.model_dump(),
            },
        )
    except (AppError, Exception) as e:
        raise e


@router.patch(
    "/user",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        201: {"model": GenericResponseModel[UserRead]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def update_user_api(
    user_updates: UserUpdate,
    user: UserRead = Depends(get_current_user_from_jwt_token),
):
    """
    Update current authenticated user's profile.
    """
    try:
        user_db = UserService().get_user(user_email=user.email)
        response = UserService().update_user(
            user_id=user_db.id,
            user_data=user_updates,
        )
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content={
                "message": UserResponseMessages.USER_UPDATED.value,
                "data": response.model_dump(),
            },
        )
    except (AppError, Exception) as e:
        raise e


@router.get(
    "/user/companies",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[PaginatedResponse[CompanyRead]]},
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def get_user_companies_api(
    params: CompanyQueryParams = Depends(),
    user: UserRead = Depends(get_current_user_from_jwt_token),
):
    """
    Get all companies the authenticated user is associated with.

    - **Supports**: Filtering by role, name, industry, etc.
    - **Returns**: Paginated list of companies
    """
    try:
        response = UserService().get_user_companies(params=params, user=user)
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=GenericResponseModel(
                message=CompanyUserResponseMessages.GET_COMPANY_USERS.value,
                data=response.model_dump(),
            ).model_dump(),
        )
    except (AppError, Exception) as e:
        raise e
