from uuid import UUID

from fastapi import APIRouter, Depends, Path, status
from fastapi.responses import JSONResponse

from app.api.dependencies.common import CommonJWTRouteDependencies
from app.models.app_error import AppErrorResponseModel
from app.models.company.response_messages import CompanyRoleResponseMessages
from app.models.company.roles import (
    RoleCreateModel,
    RoleDeleteModel,
    RoleQueryParamsModel,
    RoleReadModel,
    RoleUpdateModel,
)
from app.models.generic_pagination import PaginatedResponse
from app.models.generic_response import GenericResponseModel
from app.models.tags import UserverseApiTag
from app.services.company.role import RoleService
from app.utils.shared_context import SharedContext

router = APIRouter()
tag = UserverseApiTag.COMPANY_ROLE_MANAGEMENT.name


@router.post(
    "/company/{company_id}/role",
    tags=[tag],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": GenericResponseModel[RoleReadModel]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def create_role_api(
    payload: RoleCreateModel,
    company_id: UUID = Path(..., description="The unique identifier of the company"),
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.create_role_for_company(payload=payload, company_id=company_id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": CompanyRoleResponseMessages.ROLE_CREATION_SUCCESS.value,
            "data": response.model_dump(mode="json"),
        },
    )


@router.patch(
    "/company/{company_id}/role/{name}",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[RoleReadModel]},
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def update_role_api(
    payload: RoleUpdateModel,
    company_id: UUID,
    name: str,
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.update_company_role(
        company_id=company_id,
        name=name,
        payload=payload,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": CompanyRoleResponseMessages.ROLE_UPDATED.value,
            "data": response.model_dump(mode="json"),
        },
    )


@router.delete(
    "/company/{company_id}/role",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[dict]},
        400: {"model": AppErrorResponseModel},
        404: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def delete_role_api(
    payload: RoleDeleteModel,
    company_id: UUID = Path(..., description="Company ID to delete role from"),
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.delete_role(payload=payload, company_id=company_id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content={
            "message": CompanyRoleResponseMessages.ROLE_DELETED.value,
            "data": response,
        },
    )


@router.get(
    "/company/{company_id}/roles",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[PaginatedResponse[RoleReadModel]]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def get_company_roles_api(
    company_id: UUID = Path(..., description="ID of the company whose roles to fetch"),
    query_params: RoleQueryParamsModel = Depends(),
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.get_company_roles(payload=query_params, company_id=company_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=GenericResponseModel(
            message=CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value,
            data=response.model_dump(mode="json"),
        ).model_dump(mode="json"),
    )


@router.post(
    "/company/{company_id}/roles/{role_id}",
    tags=[tag],
    status_code=status.HTTP_201_CREATED,
    responses={
        201: {"model": GenericResponseModel[RoleReadModel]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def assign_role_to_company_api(
    company_id: UUID,
    role_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.assign_role_to_company(company_id=company_id, role_id=role_id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=GenericResponseModel(
            message=CompanyRoleResponseMessages.ROLE_CREATION_SUCCESS.value,
            data=response.model_dump(mode="json"),
        ).model_dump(mode="json"),
    )


@router.delete(
    "/company/{company_id}/roles/{role_id}",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[dict]},
        400: {"model": AppErrorResponseModel},
        500: {"model": AppErrorResponseModel},
    },
)
def unassign_role_from_company_api(
    company_id: UUID,
    role_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.unassign_role(company_id=company_id, role_id=role_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=GenericResponseModel(
            message=CompanyRoleResponseMessages.ROLE_DELETED.value,
            data=response,
        ).model_dump(mode="json"),
    )
