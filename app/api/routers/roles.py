from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.dependencies.common import CommonJWTRouteDependencies
from app.models.app_error import AppErrorResponseModel
from app.models.company.response_messages import CompanyRoleResponseMessages
from app.models.company.roles import (
    RoleAssignCompaniesModel,
    RoleCreateModel,
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


@router.post("/roles", tags=[tag], status_code=status.HTTP_201_CREATED)
def create_role_api(
    payload: RoleCreateModel,
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.create_role(payload)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=GenericResponseModel(
            message=CompanyRoleResponseMessages.ROLE_CREATION_SUCCESS.value,
            data=response.model_dump(mode="json"),
        ).model_dump(mode="json"),
    )


@router.get(
    "/roles",
    tags=[tag],
    status_code=status.HTTP_200_OK,
    responses={
        200: {"model": GenericResponseModel[PaginatedResponse[RoleReadModel]]},
        400: {"model": AppErrorResponseModel},
    },
)
def get_roles_api(
    query_params: RoleQueryParamsModel = Depends(),
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.get_roles(payload=query_params)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=GenericResponseModel(
            message=CompanyRoleResponseMessages.ROLE_GET_SUCCESS.value,
            data=response.model_dump(mode="json"),
        ).model_dump(mode="json"),
    )


@router.patch("/roles/{role_id}", tags=[tag], status_code=status.HTTP_200_OK)
def update_role_api(
    role_id: UUID,
    payload: RoleUpdateModel,
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.update_role(role_id=role_id, payload=payload)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=GenericResponseModel(
            message=CompanyRoleResponseMessages.ROLE_UPDATED.value,
            data=response.model_dump(mode="json"),
        ).model_dump(mode="json"),
    )


@router.delete("/roles/{role_id}", tags=[tag], status_code=status.HTTP_200_OK)
def delete_role_api(
    role_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.delete_global_role(role_id=role_id)
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=GenericResponseModel(
            message=CompanyRoleResponseMessages.ROLE_DELETED.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.post("/roles/{role_id}/companies", tags=[tag], status_code=status.HTTP_201_CREATED)
def assign_role_to_companies_api(
    role_id: UUID,
    payload: RoleAssignCompaniesModel,
    common: CommonJWTRouteDependencies = Depends(),
):
    service = RoleService(SharedContext(user=common.user, db_session=common.session))
    response = service.assign_role_to_companies(role_id=role_id, payload=payload)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=GenericResponseModel(
            message=CompanyRoleResponseMessages.ROLE_CREATION_SUCCESS.value,
            data=response,
        ).model_dump(mode="json"),
    )
