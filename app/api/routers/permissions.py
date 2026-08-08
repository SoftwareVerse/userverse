from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.dependencies.common import CommonJWTRouteDependencies
from app.models.app_error import AppErrorResponseModel
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

router = APIRouter(tags=["Global Permission Management"])


def _service(common: CommonJWTRouteDependencies) -> PermissionService:
    return PermissionService(SharedContext(user=common.user, db_session=common.session))


@router.post(
    "/permissions",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel[PermissionReadModel],
    responses={
        403: {"model": AppErrorResponseModel},
        409: {"model": AppErrorResponseModel},
    },
)
def create_global_permission_api(
    payload: PermissionCreateModel,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).create_global_permission(payload)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=GenericResponseModel(
            message=PermissionResponseMessages.CREATED.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.get(
    "/permissions",
    response_model=GenericResponseModel[PaginatedResponse[PermissionReadModel]],
)
def get_global_permissions_api(
    query_params: PermissionQueryParamsModel = Depends(),
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).get_global_permissions(query_params)
    return JSONResponse(
        content=GenericResponseModel(
            message=PermissionResponseMessages.FOUND.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.patch(
    "/permissions/{permission_id}",
    response_model=GenericResponseModel[PermissionReadModel],
)
def update_global_permission_api(
    permission_id: UUID,
    payload: PermissionUpdateModel,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).update_global_permission(permission_id, payload)
    return JSONResponse(
        content=GenericResponseModel(
            message=PermissionResponseMessages.UPDATED.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.delete(
    "/permissions/{permission_id}",
    response_model=GenericResponseModel[dict],
)
def delete_global_permission_api(
    permission_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).delete_global_permission(permission_id)
    return JSONResponse(
        content=GenericResponseModel(
            message=PermissionResponseMessages.DELETED.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.get(
    "/roles/{role_id}/permissions",
    response_model=GenericResponseModel[list[PermissionReadModel]],
)
def get_global_role_permissions_api(
    role_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).get_global_role_permissions(role_id)
    return JSONResponse(
        content=GenericResponseModel(
            message=PermissionResponseMessages.FOUND.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.post(
    "/roles/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel[RoleReadModel],
)
def assign_global_permission_api(
    role_id: UUID,
    permission_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).assign_global_permission(role_id, permission_id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=GenericResponseModel(
            message=PermissionResponseMessages.ASSIGNED.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    response_model=GenericResponseModel[RoleReadModel],
)
def remove_global_permission_api(
    role_id: UUID,
    permission_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).remove_global_permission(role_id, permission_id)
    return JSONResponse(
        content=GenericResponseModel(
            message=PermissionResponseMessages.UNASSIGNED.value,
            data=response,
        ).model_dump(mode="json"),
    )
