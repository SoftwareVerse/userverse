from app.dependencies.common import CommonJWTRouteDependencies
from fastapi import APIRouter, Depends, status, Path
from fastapi.responses import JSONResponse

# Models
from app.models.company.user import CompanyUserAddModel, CompanyUserReadModel
from app.models.generic_pagination import PaginatedResponse
from app.models.generic_response import GenericResponseModel
from app.models.company.company import CompanyReadModel
from app.models.app_error import AppErrorResponseModel
from app.models.company.response_messages import CompanyUserResponseMessages

# Auth and security
from app.models.tags import UserverseApiTag
from app.models.user.user import UserQueryParams

# Logic layer
from app.logic.company.user import CompanyUserService

# Utilities
from app.utils.app_error import AppError
from app.utils.shared_context import SharedContext

router = APIRouter()
tag = UserverseApiTag.COMPANY_USER_MANAGEMENT.name
company_id_description = "The ID of the company"


@router.get(
    "/company/{company_id}/users",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[PaginatedResponse[CompanyUserReadModel]]},
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def get_company_users_api(
    company_id: int = Path(..., description=company_id_description),
    params: UserQueryParams = Depends(),
    common_dependecies: CommonJWTRouteDependencies = Depends(),
):
    """
    Get a paginated list of users associated with a specific company.

    - **Requires**: Authenticated user
    - **Supports**: Query parameters for filtering, sorting, pagination
    """
    try:
        context = SharedContext(
            user=common_dependecies.user,
            db_session=common_dependecies.session,
        )
        service = CompanyUserService(context)
        response = service.get_company_user(
            company_id=company_id,
            params=params,
        )

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=GenericResponseModel(
                message=CompanyUserResponseMessages.GET_COMPANY_USERS.value,
                data=response.model_dump(),
            ).model_dump(),
        )
    except (AppError, Exception) as e:
        raise e


@router.post(
    "/company/{company_id}/users",
    tags=[tag],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": GenericResponseModel[CompanyReadModel]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def add_user_to_company_api(
    payload: CompanyUserAddModel,
    company_id: int = Path(..., description=company_id_description),
    common_dependecies: CommonJWTRouteDependencies = Depends(),
):
    """
    Add a user to a company with a specified role.

    - **Requires**: Authenticated user
    - **Returns**: The updated company info or user assignment info
    """
    try:
        context = SharedContext(
            user=common_dependecies.user,
            db_session=common_dependecies.session,
        )
        response = CompanyUserService(context).add_user_to_company(
            company_id=company_id,
            payload=payload,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=GenericResponseModel(
                message=CompanyUserResponseMessages.ADD_USER_SUCCESS.value,
                data=response.model_dump(),
            ).model_dump(),
        )
    except (AppError, Exception) as e:
        raise e


@router.delete(
    "/company/{company_id}/user/{user_id}",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        201: {"model": GenericResponseModel[CompanyUserReadModel]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def delete_user_from_company_api(
    company_id: int = Path(..., description=company_id_description),
    user_id: int = Path(..., description="The ID of the user to remove"),
    common_dependecies: CommonJWTRouteDependencies = Depends(),
):
    """
    Remove a specific user from a company.

    - **Requires**: Authenticated user
    - **Returns**: The removed user's data
    """
    try:
        context = SharedContext(
            user=common_dependecies.user,
            db_session=common_dependecies.session,
        )
        response = CompanyUserService(context).remove_user_from_company(
            company_id=company_id,
            user_id=user_id,
        )

        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=GenericResponseModel(
                message=CompanyUserResponseMessages.REMOVE_USER_SUCCESS.value,
                data=response.model_dump(),
            ).model_dump(),
        )
    except (AppError, Exception) as e:
        raise e
