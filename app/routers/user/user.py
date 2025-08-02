from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

# Tags & Models
from app.dependencies.common import (
    CommonBasicAuthRouteDependencies,
    CommonJWTRouteDependencies,
)
from app.models.tags import UserverseApiTag
from app.models.user.response_messages import UserResponseMessages
from app.models.user.user import (
    TokenResponseModel,
    UserCreateModel,
    UserReadModel,
    UserUpdateModel,
)
from app.models.company.company import CompanyQueryParams, CompanyRead
from app.models.company.response_messages import (
    CompanyUserResponseMessages,
)
from app.models.generic_response import GenericResponseModel
from app.models.generic_pagination import PaginatedResponse
from app.models.app_error import AppErrorResponseModel

# Logic
from app.logic.user.user import UserService

router = APIRouter(
    prefix="/user",
    tags=[UserverseApiTag.USER_MANAGEMENT.name],
    responses={
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)


@router.patch(
    "/login",
    description=UserverseApiTag.USER_MANAGEMENT_BASIC_AUTH.description,
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenericResponseModel[TokenResponseModel],
)
def user_login_api(
    common_dependecies: CommonBasicAuthRouteDependencies = Depends(),
):
    """
    Authenticate user using basic auth credentials.

    - **Returns**: Access token for future authenticated requests
    """

    response = UserService().user_login(user_credentials=common_dependecies.user)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": UserResponseMessages.USER_LOGGED_IN.value,
            "data": response.model_dump(),
        },
    )


@router.post(
    "/create",
    description=UserverseApiTag.USER_MANAGEMENT_BASIC_AUTH.description,
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel[UserReadModel],
)
def create_user_api(
    user: UserCreateModel,
    common_dependecies: CommonBasicAuthRouteDependencies = Depends(),
):
    """
    Create a new user account.

    - **Requires**: Valid basic auth credentials
    - **Returns**: Created user details
    """
    response = UserService().create_user(
        user_credentials=common_dependecies.user,
        user_data=user,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": UserResponseMessages.USER_CREATED.value,
            "data": response.model_dump(),
        },
    )


@router.get(
    "/get",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel[UserReadModel],
)
def get_user_api(
    common_dependecies: CommonJWTRouteDependencies = Depends(),
):
    """
    Retrieve current authenticated user's details.
    """

    response = UserService().get_user(user_email=common_dependecies.user.email)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": UserResponseMessages.USER_FOUND.value,
            "data": response.model_dump(),
        },
    )


@router.patch(
    "/update",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel[UserReadModel],
)
def update_user_api(
    user_updates: UserUpdateModel,
    common_dependecies: CommonJWTRouteDependencies = Depends(),
):
    """
    Update current authenticated user's profile.
    """

    user_db = UserService().get_user(user_email=common_dependecies.user.email)
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


@router.get(
    "/companies",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel[PaginatedResponse[CompanyRead]],
)
def get_user_companies_api(
    params: CompanyQueryParams = Depends(),
    common_dependecies: CommonJWTRouteDependencies = Depends(),
):
    """
    Get all companies the authenticated user is associated with.

    - **Supports**: Filtering by role, name, industry, etc.
    - **Returns**: Paginated list of companies
    """

    response = UserService().get_user_companies(
        params=params, user=common_dependecies.user
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=GenericResponseModel(
            message=CompanyUserResponseMessages.GET_COMPANY_USERS.value,
            data=response.model_dump(),
        ).model_dump(),
    )
