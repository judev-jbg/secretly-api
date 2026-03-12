"""Esquemas Pydantic para los endpoints de autenticación."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """Payload para registrar un nuevo usuario."""
    email: EmailStr = Field(
        description="Correo electrónico del usuario",
        examples=["user@example.com"],
    )
    password: str = Field(
        description="Contraseña en texto plano (se hashea con bcrypt en el servidor)",
        examples=["S3cur3P@ssw0rd!"],
    )
    salt: str = Field(
        description="Salt generado en el cliente para derivación de claves de cifrado",
        examples=["a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"],
    )


class LoginRequest(BaseModel):
    """Payload para autenticar a un usuario."""
    email: EmailStr = Field(
        description="Correo electrónico registrado",
        examples=["user@example.com"],
    )
    password: str = Field(
        description="Contraseña del usuario",
        examples=["S3cur3P@ssw0rd!"],
    )


class LoginResponse(BaseModel):
    """Respuesta del login con tokens y salt."""
    access_token: str = Field(
        description="JWT de acceso (expira en 30 min por defecto)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    refresh_token: str = Field(
        description="JWT de refresco (expira en 7 días por defecto)",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Tipo de token para el header Authorization",
    )
    salt: str = Field(
        description="Salt del usuario para derivar la clave de cifrado en el cliente",
        examples=["a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6"],
    )


class RefreshRequest(BaseModel):
    """Payload para refrescar el access token."""
    refresh_token: str = Field(
        description="Refresh token obtenido en el login",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )


class RefreshResponse(BaseModel):
    """Respuesta con el nuevo access token."""
    access_token: str = Field(
        description="Nuevo JWT de acceso",
        examples=["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."],
    )
    token_type: str = Field(
        default="bearer",
        description="Tipo de token para el header Authorization",
    )


class ForgotPasswordRequest(BaseModel):
    """Payload para solicitar el reset de contraseña."""
    email: EmailStr = Field(
        description="Correo electrónico del usuario que quiere resetear su contraseña",
        examples=["user@example.com"],
    )


class ResetPasswordRequest(BaseModel):
    """Payload para aplicar el reset de contraseña."""
    token: str = Field(
        description="Token de reset recibido por email (UUID, expira en 15 min)",
        examples=["550e8400-e29b-41d4-a716-446655440000"],
    )
    new_password: str = Field(
        description="Nueva contraseña del usuario",
        examples=["N3wS3cur3P@ss!"],
    )


class MessageResponse(BaseModel):
    """Respuesta genérica con mensaje informativo."""
    message: str = Field(
        description="Mensaje descriptivo del resultado de la operación",
        examples=["User registered successfully"],
    )
