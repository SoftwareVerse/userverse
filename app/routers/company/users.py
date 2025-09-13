from app.dependencies.common import CommonJWTRouteDependencies
from fastapi import APIRouter, Depends, status, Path
from fastapi.responses import JSONResponse

# Models
from app.models.company.user import CompanyUserAdd, CompanyUserRead
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

router = APIRouter()
tag = UserverseApiTag.COMPANY_USER_MANAGEMENT.name
company_id_description = "The ID of the company"


@router.get(
    "/company/{company_id}/users",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[PaginatedResponse[CompanyUserRead]]},
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
        service = CompanyUserService()
        response = service.get_company_user(
            company_id=company_id, params=params, user=common_dependecies.user
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
    company_id: int = Path(..., description=company_id_description),
    payload: CompanyUserAdd = Depends(),
    common_dependecies: CommonJWTRouteDependencies = Depends(),
):
    """
    Add a user to a company with a specified role.

    - **Requires**: Authenticated user
    - **Returns**: The updated company info or user assignment info
    """
    try:
        response = CompanyUserService().add_user_to_company(
            company_id=company_id, payload=payload, added_by=common_dependecies.user
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
        201: {"model": GenericResponseModel[CompanyUserRead]},
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
        response = CompanyUserService().remove_user_from_company(
            company_id=company_id, user_id=user_id, removed_by=common_dependecies.user
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
