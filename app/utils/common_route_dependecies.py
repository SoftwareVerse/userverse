# app/dependencies/common.py
from sqlalchemy.orm import Session
from fastapi import Depends
from app.security.jwt import get_current_user_from_jwt_token
from app.security.basic_auth import get_basic_auth_credentials
from app.database.session_manager import get_session
from app.models.user.user import UserLogin
from app.models.user.user import UserRead

class CommonJWTRouteDependencies:
    def __init__(
        self,
        session: Session = Depends(get_session),
        user: UserRead = Depends(get_current_user_from_jwt_token),
    ):
        self.session = session
        self.user = user
        
        
class CommonBasicAuthRouteDependencies:
    def __init__(
        self,
        session: Session = Depends(get_session),
        user: UserLogin = Depends(get_basic_auth_credentials),
    ):
        self.session = session
        self.user = user