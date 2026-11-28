from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field

import auth_db
import insight_history
from security import (
    create_access_token,
    decode_access_token,
    token_expiry_minutes,
    verify_password,
)


router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
UNAUTHORIZED_DETAIL = "Authentication required."
INVALID_TOKEN_DETAIL = "Invalid or expired token."
FORBIDDEN_DETAIL = "Your role does not allow this action."


def _unauthorized(detail=UNAUTHORIZED_DETAIL):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(token: str | None = Depends(oauth2_scheme)):
    if not token:
        raise _unauthorized()

    payload = decode_access_token(token)
    if payload is None:
        raise _unauthorized(INVALID_TOKEN_DETAIL)

    try:
        user_id = int(payload["sub"])
    except (KeyError, TypeError, ValueError) as error:
        raise _unauthorized(INVALID_TOKEN_DETAIL) from error

    user = auth_db.get_user_by_id(user_id)
    if user is None or not user["is_active"]:
        raise _unauthorized(INVALID_TOKEN_DETAIL)

    if int(payload.get("ver", -1)) != auth_db.get_token_version(user_id):
        raise _unauthorized("This session has ended. Please sign in again.")

    return user


def require_roles(*allowed_roles):
    def dependency(current_user=Depends(get_current_user)):
        if current_user["role"] not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=FORBIDDEN_DETAIL,
            )
        return current_user

    return dependency


current_admin = require_roles("admin")
current_writer = require_roles("admin", "analyst")


class RegisterRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=254)
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="viewer", max_length=20)


class LoginRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class ProfileUpdateRequest(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=100)
    email: str | None = Field(default=None, pattern=EMAIL_PATTERN, max_length=254)
    current_password: str | None = Field(default=None, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class AdminCreateUserRequest(BaseModel):
    email: str = Field(pattern=EMAIL_PATTERN, max_length=254)
    full_name: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="viewer", max_length=20)
    is_active: bool = True


class AdminUserUpdateRequest(BaseModel):
    role: str | None = Field(default=None, max_length=20)
    is_active: bool | None = None


def _token_response(user):
    return {
        "access_token": create_access_token(user),
        "token_type": "bearer",
        "expires_in": token_expiry_minutes() * 60,
        "user": user,
    }


@router.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(request: RegisterRequest):
    if request.role not in auth_db.ROLES:
        raise HTTPException(status_code=400, detail="Unsupported role.")

    is_first_user = auth_db.count_users() == 0
    if is_first_user and request.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="The first account must be created with the Admin role.",
        )
    if not is_first_user and request.role != "viewer":
        raise HTTPException(
            status_code=403,
            detail="Public registration is limited to the Viewer role.",
        )

    try:
        user = auth_db.create_user(
            email=request.email,
            full_name=request.full_name,
            password=request.password,
            role=request.role,
        )
        if is_first_user:
            insight_history.claim_orphan_insights(user["id"])
    except auth_db.DuplicateEmail as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {
        "message": "Account created successfully.",
        "user": user,
    }


@router.post("/auth/login")
def login(request: LoginRequest):
    user = auth_db.get_user_by_email(request.email.strip().lower())

    if user is None or not user["is_active"]:
        raise _unauthorized("Incorrect email or password.")

    stored_hash = auth_db.get_password_hash(user["id"])
    if not stored_hash or not verify_password(request.password, stored_hash):
        raise _unauthorized("Incorrect email or password.")

    return _token_response(user)


@router.get("/auth/me")
def read_current_user(current_user=Depends(get_current_user)):
    return current_user


@router.post("/auth/logout")
def logout(current_user=Depends(get_current_user)):
    auth_db.increment_token_version(current_user["id"])
    return {"message": "Logged out successfully."}


@router.patch("/auth/profile")
def update_profile(
    request: ProfileUpdateRequest,
    current_user=Depends(get_current_user),
):
    if request.new_password and not request.current_password:
        raise HTTPException(
            status_code=400,
            detail="Current password is required to set a new password.",
        )

    if request.current_password:
        stored_hash = auth_db.get_password_hash(current_user["id"])
        if not stored_hash or not verify_password(
            request.current_password, stored_hash
        ):
            raise HTTPException(
                status_code=400,
                detail="Current password is incorrect.",
            )

    try:
        user = auth_db.update_user(
            current_user["id"],
            full_name=request.full_name,
            email=request.email,
            password=request.new_password,
        )
    except auth_db.DuplicateEmail as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {
        "message": (
            "Profile updated. Please sign in again."
            if request.new_password
            else "Profile updated successfully."
        ),
        "user": user,
    }


@router.post("/auth/change-password")
def change_password(
    request: ChangePasswordRequest,
    current_user=Depends(get_current_user),
):
    stored_hash = auth_db.get_password_hash(current_user["id"])
    if not stored_hash or not verify_password(
        request.current_password, stored_hash
    ):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")

    auth_db.update_user(
        current_user["id"], password=request.new_password
    )
    return {"message": "Password updated. Please sign in again."}


@router.get("/admin/users")
def admin_list_users(
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user=Depends(current_admin),
):
    return auth_db.list_users(limit=limit, offset=offset)


@router.post("/admin/users", status_code=status.HTTP_201_CREATED)
def admin_create_user(
    request: AdminCreateUserRequest,
    current_user=Depends(current_admin),
):
    if request.role not in auth_db.ROLES:
        raise HTTPException(status_code=400, detail="Unsupported role.")

    try:
        user = auth_db.create_user(
            email=request.email,
            full_name=request.full_name,
            password=request.password,
            role=request.role,
            is_active=request.is_active,
        )
    except auth_db.DuplicateEmail as error:
        raise HTTPException(status_code=409, detail=str(error)) from error

    return {"message": "User created successfully.", "user": user}


@router.patch("/admin/users/{user_id}")
def admin_update_user(
    user_id: int,
    request: AdminUserUpdateRequest,
    current_user=Depends(current_admin),
):
    if request.role is not None and request.role not in auth_db.ROLES:
        raise HTTPException(status_code=400, detail="Unsupported role.")
    if user_id == current_user["id"] and request.is_active is False:
        raise HTTPException(
            status_code=400, detail="Administrators cannot deactivate themselves."
        )

    try:
        if request.role is not None:
            user = auth_db.set_role(user_id, request.role)
        else:
            user = auth_db.get_user_by_id(user_id)
        if request.is_active is not None:
            user = auth_db.set_active(user_id, request.is_active)
    except auth_db.UserNotFound as error:
        raise HTTPException(status_code=404, detail=str(error)) from error

    return {"message": "User updated successfully.", "user": user}
