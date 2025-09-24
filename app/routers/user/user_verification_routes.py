from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.responses import JSONResponse

# Tags & Models
from app.models.tags import UserverseApiTag
from app.models.user.response_messages import UserResponseMessages
from app.models.generic_response import GenericResponseModel
from app.models.app_error import AppErrorResponseModel

# Logic
from app.logic.user.verification import UserVerificationService
from app.logic.user.basic_auth import UserBasicAuthService
from app.utils.shared_context import SharedContext
from app.dependencies.common import CommonJWTRouteDependencies
from sqlalchemy.orm import Session
from app.database.session_manager import get_session

router = APIRouter(
    prefix="/user",
    tags=[UserverseApiTag.USER_VERIFICATION.name],
    responses={
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)


@router.get(
    "/verify",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel[None],
)
def verify_user_account(token: str, session: Session = Depends(get_session)):
    """
    Verify user account using the provided token.
    - **Requires**: Token from email verification link
    - **Returns**: Success message on verification
    """
    response = UserVerificationService(session).verify_user_account(token=token)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=GenericResponseModel(message=response, data=None).model_dump(),
    )


@router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel[None],
)
def resend_verification_email(
    background_tasks: BackgroundTasks,
    common: CommonJWTRouteDependencies = Depends(),
):
    """
    Resend verification email to the user.
    - **Requires**: JWT token for authentication
    - **Returns**: Success message on email resend
    """
    service = UserBasicAuthService(
        SharedContext(configs={}, user=common.user, db_session=common.session)
    )
    service.send_verification_email(
        mode="verify", background_tasks=background_tasks
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=GenericResponseModel(
            message=UserResponseMessages.VERIFICATION_EMAIL_RESENT.value,
            data=None,
        ).model_dump(),
    )
