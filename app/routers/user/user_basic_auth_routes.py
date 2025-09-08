from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

# Dependencies
from app.dependencies.common import CommonBasicAuthRouteDependencies
from app.utils.shared_context import SharedContext

# Tags & Models
from app.models.tags import UserverseApiTag
from app.models.user.response_messages import UserResponseMessages
from app.models.user.user import TokenResponseModel, UserCreateModel, UserReadModel
from app.models.generic_response import GenericResponseModel
from app.models.app_error import AppErrorResponseModel

# Logic
from app.logic.user.basic_auth import UserBasicAuthService

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
    "/create",
    description=UserverseApiTag.USER_MANAGEMENT_BASIC_AUTH.description,
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel[UserReadModel],
)
def create_user_api(
    user: UserCreateModel,
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
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": UserResponseMessages.USER_CREATED.value,
            "data": response.model_dump(),
        },
    )
