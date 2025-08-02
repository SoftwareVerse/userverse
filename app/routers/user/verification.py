from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

# Tags & Models
from app.models.tags import UserverseApiTag
from app.models.user.response_messages import UserResponseMessages
from app.models.generic_response import GenericResponseModel
from app.models.app_error import AppErrorResponseModel

# Logic
from app.logic.user.user import UserService
from app.utils.shared_context import SharedContext
from app.dependencies.common import CommonJWTRouteDependencies

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
    "/verify",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel[None],
)
def verify_user_account(token: str):
    response = UserService.verify_user_account(token=token)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=GenericResponseModel(message=response, data=None),
    )


@router.post(
    "/resend-verification",
    status_code=status.HTTP_200_OK,
    response_model=GenericResponseModel[None],
)
def resend_verification_email(
    common: CommonJWTRouteDependencies = Depends(),
):
    service = UserService(
        SharedContext(configs={}, user=common.user, db_session=common.session)
    )
    service.send_verification_email(mode="verify")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=GenericResponseModel(
            message=UserResponseMessages.VERIFICATION_EMAIL_RESENT.value,
            data=None,
        ),
    )
