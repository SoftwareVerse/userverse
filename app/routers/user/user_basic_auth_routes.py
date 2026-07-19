from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

# Dependencies
from app.dependencies.common import CommonBasicAuthRouteDependencies
from app.repository.database.session_manager import get_session
from app.utils.shared_context import SharedContext

# Tags & Models
from app.models.tags import UserverseApiTag
from app.models.user.response_messages import UserResponseMessages
from app.models.user.user import (
    RefreshTokenRequestModel,
    TokenResponseModel,
    TokenRevocationResponseModel,
    UserCreateModel,
    UserReadModel,
)
from app.models.generic_response import GenericResponseModel
from app.models.app_error import AppErrorResponseModel

# Logic
from app.services.user.basic_auth import UserBasicAuthService

router = APIRouter(
    prefix="/user",
    tags=[UserverseApiTag.USER_MANAGEMENT_BASIC_AUTH.name],
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
    common: CommonBasicAuthRouteDependencies = Depends(),
):
    """
    User login API endpoint.
    - **Requires**: Basic Auth (email as username, password as password)
    - **Returns**: JWT token on successful login
    """
    service = UserBasicAuthService(SharedContext(user=None, db_session=common.session))
    response = service.user_login(user_credentials=common.user)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": UserResponseMessages.USER_LOGGED_IN.value,
            "data": response.model_dump(),
        },
    )


@router.post(
    "/refresh",
    description=UserverseApiTag.USER_MANAGEMENT_BASIC_AUTH.description,
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenericResponseModel[TokenResponseModel],
)
def refresh_user_token_api(
    payload: RefreshTokenRequestModel,
    session: Session = Depends(get_session),
):
    """
    Refresh user token API endpoint.
    - **Requires**: A valid refresh token in the request body
    - **Returns**: Fresh access and refresh tokens
    """
    service = UserBasicAuthService(SharedContext(user=None, db_session=session))
    response = service.refresh_user_token(refresh_token=payload.refresh_token)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content={
            "message": UserResponseMessages.USER_TOKEN_REFRESHED.value,
            "data": response.model_dump(),
        },
    )


@router.post(
    "/revoke",
    description=UserverseApiTag.USER_MANAGEMENT_BASIC_AUTH.description,
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel[TokenRevocationResponseModel],
)
def revoke_refresh_token_api(
    payload: RefreshTokenRequestModel,
    session: Session = Depends(get_session),
):
    """
    Revoke refresh tokens API endpoint.
    - **Requires**: A valid refresh token in the request body
    - **Returns**: Revocation confirmation
    """
    service = UserBasicAuthService(SharedContext(user=None, db_session=session))
    service.revoke_refresh_token(refresh_token=payload.refresh_token)
    response = TokenRevocationResponseModel(revoked=True)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": UserResponseMessages.USER_REFRESH_TOKEN_REVOKED.value,
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
    background_tasks: BackgroundTasks,
    common: CommonBasicAuthRouteDependencies = Depends(),
):
    """
    Create a new user API endpoint.
    - **Requires**: Basic Auth (email as username, password as password)
    - **Returns**: Created user data on successful creation
    """
    service = UserBasicAuthService(SharedContext(user=None, db_session=common.session))
    response = service.create_user(
        user_credentials=common.user,
        user_data=user,
        background_tasks=background_tasks,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": UserResponseMessages.USER_CREATED.value,
            "data": response.model_dump(),
        },
    )
