"""Esquemas Pydantic para los endpoints de autenticación."""

from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    """Payload para registrar un nuevo usuario."""
    email: EmailStr
    password: str
    salt: str


class LoginRequest(BaseModel):
    """Payload para autenticar a un usuario."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """Respuesta del login con tokens y salt."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    salt: str


class RefreshRequest(BaseModel):
    """Payload para refrescar el access token."""
    refresh_token: str


class RefreshResponse(BaseModel):
    """Respuesta con el nuevo access token."""
    access_token: str
    token_type: str = "bearer"


class ForgotPasswordRequest(BaseModel):
    """Payload para solicitar el reset de contraseña."""
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Payload para aplicar el reset de contraseña."""
    token: str
    new_password: str


class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje informativo."""
    message: str
