from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

# Tags & Models
from app.dependencies.common import CommonJWTRouteDependencies

from app.models.tags import UserverseApiTag
from app.models.user.response_messages import UserResponseMessages
from app.models.user.user import (
    UserReadModel,
    UserUpdateModel,
)
from app.models.company.company import CompanyQueryParams, CompanyRead
from app.models.company.response_messages import CompanyUserResponseMessages
from app.models.generic_response import GenericResponseModel
from app.models.generic_pagination import PaginatedResponse
from app.models.app_error import AppErrorResponseModel

# Logic
from app.logic.user.user import UserService
from app.utils.shared_context import SharedContext

router = APIRouter(
    prefix="/user",
    tags=[UserverseApiTag.USER_MANAGEMENT.name],
    responses={
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)


@router.get(
    "/get",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel[UserReadModel],
)
def get_user_api(
    common: CommonJWTRouteDependencies = Depends(),
):
    """
    Get user details API endpoint.
    - **Requires**: JWT token for authentication
    - **Returns**: User details on successful retrieval
    """
    service = UserService(
        SharedContext(configs={}, user=common.user, db_session=common.session)
    )
    response = service.get_user(user_email=common.user.email)
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
    common: CommonJWTRouteDependencies = Depends(),
):
    """
    Update user details API endpoint.
    - **Requires**: JWT token for authentication
    - **Returns**: Updated user details on successful update
    """
    service = UserService(
        SharedContext(configs={}, user=common.user, db_session=common.session)
    )
    user_db = service.get_user(user_email=common.user.email)
    response = service.update_user(
        user_id=user_db.id,
        user_data=user_updates,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
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
    common: CommonJWTRouteDependencies = Depends(),
):
    """
    Get companies associated with the user API endpoint.
    - **Requires**: JWT token for authentication
    - **Returns**: List of companies associated with the user
    """

    service = UserService(
        SharedContext(
            configs={},
            user=common.user,
            db_session=common.session,
            enforce_status_check=True,
        )
    )
    response = service.get_user_companies(params=params)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=GenericResponseModel(
            message=CompanyUserResponseMessages.GET_COMPANY_USERS.value,
            data=response.model_dump(),
        ).model_dump(),
    )
