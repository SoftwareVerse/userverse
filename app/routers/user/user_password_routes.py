from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from pydantic import EmailStr

# Tags & Models
from app.models.app_error import AppErrorResponseModel
from app.models.generic_response import GenericResponseModel
from app.models.tags import UserverseApiTag

# Auth & Logic
from app.dependencies.common import CommonBasicAuthRouteDependencies
from app.logic.user.password import UserPasswordService
from app.database.session_manager import get_session
from sqlalchemy.orm import Session


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
    email: EmailStr, session: Session = Depends(get_session)
):
    """
    Trigger a password reset request.

    - **Sends**: OTP code to user's email
    - **Returns**: Success message
    """
    response = UserPasswordService(session).request_password_reset(email)
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response.model_dump(),
    )


@router.patch(
    "/validate-otp",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=GenericResponseModel[None],
)
def password_reset_validate_otp_api(
    one_time_pin: str,
    common: CommonBasicAuthRouteDependencies = Depends(),
    session: Session = Depends(get_session),
):
    """
    Validate OTP and reset password.

    - **Requires**: Basic Auth (email as username, new password as password)
    - **Also requires**: OTP/one_time_pin provided in request body
    - **Returns**: Success message
    """

    response = UserPasswordService(session).validate_otp_and_change_password(
        user_email=common.user.email,
        new_password=common.user.password,
        otp=one_time_pin,
    )
    return JSONResponse(
        status_code=status.HTTP_202_ACCEPTED,
        content=response.model_dump(),
    )
