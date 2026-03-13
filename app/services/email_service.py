"""Servicio de envío de emails con fastapi-mail."""

import logging

from fastapi_mail import FastMail, MessageSchema, MessageType, ConnectionConfig

from app.core.config import settings

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.sender_email,
    MAIL_PASSWORD=settings.sender_password,
    MAIL_FROM=settings.sender_email,
    MAIL_PORT=settings.smtp_port,
    MAIL_SERVER=settings.smtp_server,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)

fm = FastMail(conf)


async def send_reset_email(email: str, token: str) -> None:
    """
    Envía el email de reset de contraseña con el token.
    No envía nada si el servidor SMTP no está configurado.

    :param email: Dirección del destinatario.
    :param token: Token UUID de reset.
    """
    if not settings.smtp_server or not settings.sender_email:
        logger.warning("SMTP no configurado — email de reset no enviado a %s", email)
        return

    logger.info("Enviando email de reset a %s via %s:%s", email, settings.smtp_server, settings.smtp_port)
    try:
        message = MessageSchema(
            subject="Secretly — Restablecer contraseña",
            recipients=[email],
            body=(
                f"<h3>Solicitud de restablecimiento de contraseña</h3>"
                f"<p>Usa el siguiente token para restablecer tu contraseña:</p>"
                f"<p><strong>{token}</strong></p>"
                f"<p>Este token expira en {settings.reset_token_expire_minutes} minutos.</p>"
                f"<p>Si no solicitaste este cambio, ignora este mensaje.</p>"
            ),
            subtype=MessageType.html,
        )
        await fm.send_message(message)
        logger.info("Email de reset enviado correctamente a %s", email)
    except Exception as e:
        logger.error("Error al enviar email de reset a %s: %s", email, e)
