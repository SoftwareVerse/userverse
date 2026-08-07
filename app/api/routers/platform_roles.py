from uuid import UUID

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse

from app.api.dependencies.common import CommonJWTRouteDependencies
from app.models.company.roles import RoleReadModel
from app.models.generic_response import GenericResponseModel
from app.models.permission_response_messages import PlatformRoleResponseMessages
from app.services.permission import PermissionService
from app.utils.shared_context import SharedContext

router = APIRouter(tags=["Platform Role Management"])


def _service(common: CommonJWTRouteDependencies) -> PermissionService:
    return PermissionService(SharedContext(user=common.user, db_session=common.session))


@router.get(
    "/users/{user_id}/roles",
    response_model=GenericResponseModel[list[RoleReadModel]],
)
def get_platform_roles_api(
    user_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).get_platform_roles(user_id)
    return JSONResponse(
        content=GenericResponseModel(
            message=PlatformRoleResponseMessages.FOUND.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.post(
    "/users/{user_id}/roles/{role_id}",
    status_code=status.HTTP_201_CREATED,
    response_model=GenericResponseModel[list[RoleReadModel]],
)
def assign_platform_role_api(
    user_id: UUID,
    role_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).assign_platform_role(user_id, role_id)
    return JSONResponse(
        status_code=status.HTTP_201_CREATED,
        content=GenericResponseModel(
            message=PlatformRoleResponseMessages.ASSIGNED.value,
            data=response,
        ).model_dump(mode="json"),
    )


@router.delete(
    "/users/{user_id}/roles/{role_id}",
    response_model=GenericResponseModel[list[RoleReadModel]],
)
def remove_platform_role_api(
    user_id: UUID,
    role_id: UUID,
    common: CommonJWTRouteDependencies = Depends(),
):
    response = _service(common).remove_platform_role(user_id, role_id)
    return JSONResponse(
        content=GenericResponseModel(
            message=PlatformRoleResponseMessages.UNASSIGNED.value,
            data=response,
        ).model_dump(mode="json"),
    )
