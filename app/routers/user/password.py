from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import EmailStr
# Tags & Models
from app.models.app_error import AppErrorResponseModel
from app.models.generic_response import GenericResponseModel
from app.models.tags import UserverseApiTag
from app.models.user.user import UserLoginModel

# Auth & Logic
from app.security.basic_auth import get_basic_auth_credentials
from app.logic.user.password import UserPasswordService


router = APIRouter(
    prefix="/password-reset",
    tags=[UserverseApiTag.USER_PASSWORD_MANAGEMENT.name],
    responses={
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)


@router.patch(
    "/request",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenericResponseModel[None],
)
def password_reset_request_api(
    email: EmailStr
):
    """
    Trigger a password reset request.

    - **Sends**: OTP code to user's email
    - **Returns**: Success message
    """
    response = UserPasswordService().request_password_reset(email)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response.model_dump(),
    )



@router.patch(
    "/password-reset/validate-otp",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenericResponseModel[None],
)
def password_reset_validate_otp_api(
    one_time_pin: str,
    credentials: UserLoginModel = Depends(get_basic_auth_credentials),
):
    """
    Validate OTP and reset password.

    - **Requires**: Basic Auth (email as username, new password as password)
    - **Also requires**: OTP provided in request body
    - **Returns**: Success message
    """

    response = UserPasswordService().validate_otp_and_change_password(
        user_email=credentials.email,
        new_password=credentials.password,
        otp=one_time_pin,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response.model_dump(),
    )
