"""Endpoints de autenticación: registro, login, refresh y reset de contraseña."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_token, create_access_token
from app.schemas.auth import (
    RegisterRequest,
    LoginRequest,
    LoginResponse,
    RefreshRequest,
    RefreshResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    MessageResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar usuario",
    responses={
        409: {"description": "El email ya está registrado"},
        422: {"description": "Datos de entrada inválidos"},
    },
)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """
    Registra un nuevo usuario en el sistema.

    - **email**: dirección de correo única.
    - **password**: se hashea con bcrypt antes de almacenarse.
    - **salt**: generado en el cliente para derivar claves de cifrado E2E.
    """
    try:
        auth_service.register_user(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    return {"message": "User registered successfully"}


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Iniciar sesión",
    responses={
        401: {"description": "Credenciales inválidas"},
        422: {"description": "Datos de entrada inválidos"},
    },
)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    """
    Autentica al usuario y retorna un par de tokens JWT junto con el salt.

    El **access_token** se usa como Bearer en endpoints protegidos.
    El **refresh_token** permite obtener nuevos access tokens sin re-autenticar.
    El **salt** se usa en el cliente para derivar la clave de cifrado.
    """
    try:
        result = auth_service.login_user(db, payload)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return LoginResponse(**result)


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Refrescar access token",
    responses={
        401: {"description": "Refresh token inválido o expirado"},
    },
)
def refresh(payload: RefreshRequest, db: Session = Depends(get_db)):
    """
    Emite un nuevo **access_token** a partir de un **refresh_token** válido.

    Usar cuando el access token ha expirado para evitar pedir credenciales de nuevo.
    """
    user_id = decode_token(payload.refresh_token, expected_type="refresh")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    return RefreshResponse(access_token=create_access_token(user_id))


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Solicitar reset de contraseña",
    responses={
        422: {"description": "Email inválido"},
    },
)
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Genera un token de reset de contraseña.

    Siempre retorna **200 OK** independientemente de si el email existe,
    para no revelar qué cuentas están registradas.
    """
    auth_service.create_reset_token(db, str(payload.email))
    # TODO: enviar email con el token cuando se configure SMTP
    return {"message": "If the email exists, a reset link has been sent"}


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Aplicar reset de contraseña",
    responses={
        400: {"description": "Token de reset inválido o expirado"},
        422: {"description": "Datos de entrada inválidos"},
    },
)
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Aplica el cambio de contraseña usando el token recibido por email.

    El token es de un solo uso y expira en 15 minutos.
    """
    success = auth_service.reset_password(db, payload.token, payload.new_password)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    return {"message": "Password updated successfully"}
