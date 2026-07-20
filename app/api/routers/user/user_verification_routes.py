from fastapi import APIRouter, BackgroundTasks, Depends, Request, status
from fastapi.responses import JSONResponse

# Tags & Models
from app.models.tags import UserverseApiTag
from app.models.user.response_messages import UserResponseMessages
from app.models.generic_response import GenericResponseModel
from app.models.app_error import AppErrorResponseModel
from app.models.user.password import PasswordResetRequest

# Logic
from app.services.user.verification import UserVerificationService
from sqlalchemy.orm import Session
from app.repository.database.session_manager import get_session
from app.configs import settings

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
        content=GenericResponseModel(message=response, data=None).model_dump(mode="json"),
    )


@router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel[None],
)
def resend_verification_email(
    payload: PasswordResetRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
):
    """
    Resend verification email to the user.
    - **Requires**: Email address in the request body
    - **Returns**: Success message on email resend
    """
    service = UserVerificationService(session)
    response = service.resend_verification_email(
        user_email=payload.email,
        server_url=settings.SERVER_URL,
        app_name=settings.APP_NAME,
        verification_required=settings.REQUIRE_EMAIL_VERIFICATION,
        client_ip=request.client.host if request.client else None,
        background_tasks=background_tasks,
    )
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=response.model_dump(mode="json"),
    )
