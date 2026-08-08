from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.dependencies.common import CommonJWTRouteDependencies
from app.models.company.roles import RoleReadModel
from app.models.generic_pagination import PaginatedResponse
from app.models.generic_response import GenericResponseModel
from app.models.permission_response_messages import PermissionResponseMessages
from app.models.permissions import (
    PermissionCreateModel,
    PermissionQueryParamsModel,
    PermissionReadModel,
    PermissionUpdateModel,
)
from app.services.permission import PermissionService
from app.utils.shared_context import SharedContext

router = APIRouter(tags=["Company Permission Management"])


def _service(common: CommonJWTRouteDependencies) -> PermissionService:
    return PermissionService(SharedContext(user=common.user, db_session=common.session))


@router.post(
    "/company/{company_id}/permissions",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel[PermissionReadModel],
)
def create_company_permission_api(
    company_id: UUID,
    payload: PermissionCreateModel,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).create_company_permission(company_id, payload)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=GenericResponseModel(
            message=PermissionResponseMessages.CREATED.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.get(
    "/company/{company_id}/permissions",
    response_model=GenericResponseModel[PaginatedResponse[PermissionReadModel]],
)
def get_company_permissions_api(
    company_id: UUID,
    query_params: PermissionQueryParamsModel = Depends(),
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).get_company_permissions(company_id, query_params)
    return JSONResponse(
        content=GenericResponseModel(
            message=PermissionResponseMessages.FOUND.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.patch(
    "/company/{company_id}/permissions/{permission_id}",
    response_model=GenericResponseModel[PermissionReadModel],
)
def update_company_permission_api(
    company_id: UUID,
    permission_id: UUID,
    payload: PermissionUpdateModel,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).update_company_permission(
        company_id,
        permission_id,
        payload,
    )
    return JSONResponse(
        content=GenericResponseModel(
            message=PermissionResponseMessages.UPDATED.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.delete(
    "/company/{company_id}/permissions/{permission_id}",
    response_model=GenericResponseModel[dict],
)
def delete_company_permission_api(
    company_id: UUID,
    permission_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).delete_company_permission(company_id, permission_id)
    return JSONResponse(
        content=GenericResponseModel(
            message=PermissionResponseMessages.DELETED.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.get(
    "/company/{company_id}/roles/{role_id}/permissions",
    response_model=GenericResponseModel[list[PermissionReadModel]],
)
def get_company_role_permissions_api(
    company_id: UUID,
    role_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).get_company_role_permissions(company_id, role_id)
    return JSONResponse(
        content=GenericResponseModel(
            message=PermissionResponseMessages.FOUND.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.post(
    "/company/{company_id}/roles/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel[RoleReadModel],
)
def assign_company_permission_api(
    company_id: UUID,
    role_id: UUID,
    permission_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).assign_company_permission(
        company_id,
        role_id,
        permission_id,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=GenericResponseModel(
            message=PermissionResponseMessages.ASSIGNED.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.delete(
    "/company/{company_id}/roles/{role_id}/permissions/{permission_id}",
    response_model=GenericResponseModel[RoleReadModel],
)
def remove_company_permission_api(
    company_id: UUID,
    role_id: UUID,
    permission_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).remove_company_permission(
        company_id,
        role_id,
        permission_id,
    )
    return JSONResponse(
        content=GenericResponseModel(
            message=PermissionResponseMessages.UNASSIGNED.value,
            data=response,
        ).model_dump(mode="json"),
    )
