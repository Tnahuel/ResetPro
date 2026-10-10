"""Envio de emails sin dependencias extra: Resend (API HTTPS) o SMTP."""
import html
import json
import logging
import os
import smtplib
import ssl
import urllib.request
from email.message import EmailMessage

log = logging.getLogger("resetpro")


def proveedor():
    """Devuelve "resend", "smtp" o None segun las variables de entorno definidas."""
    if os.getenv("RESEND_API_KEY") and os.getenv("MAIL_FROM"):
        return "resend"
    if os.getenv("SMTP_HOST") and os.getenv("MAIL_FROM"):
        return "smtp"
    return None


def _resend(destino, asunto, texto, cuerpo_html):
    datos = json.dumps({
        "from": os.environ["MAIL_FROM"], "to": [destino],
        "subject": asunto, "text": texto, "html": cuerpo_html,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://api.resend.com/emails", data=datos, method="POST",
        headers={
            "Authorization": "Bearer " + os.environ["RESEND_API_KEY"],
            "Content-Type": "application/json",
            "User-Agent": "resetpro/1.0",   # Resend rechaza el User-Agent por defecto de Python
        },
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status >= 300:
            raise RuntimeError(f"Resend respondio {resp.status}")


def _smtp(destino, asunto, texto, cuerpo_html):
    msg = EmailMessage()
    msg["From"] = os.environ["MAIL_FROM"]
    msg["To"] = destino
    msg["Subject"] = asunto
    msg.set_content(texto)
    msg.add_alternative(cuerpo_html, subtype="html")

    host = os.environ["SMTP_HOST"]
    puerto = int(os.getenv("SMTP_PORT", "587"))
    usuario = os.getenv("SMTP_USER")
    clave = os.getenv("SMTP_PASSWORD")
    ctx = ssl.create_default_context()
    if puerto == 465:
        with smtplib.SMTP_SSL(host, puerto, timeout=10, context=ctx) as s:
            if usuario:
                s.login(usuario, clave or "")
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, puerto, timeout=10) as s:
            s.starttls(context=ctx)
            if usuario:
                s.login(usuario, clave or "")
            s.send_message(msg)


def enviar(destino, asunto, texto, cuerpo_html) -> bool:
    """True si el mensaje salio. Nunca lanza: un fallo de correo no debe romper la API."""
    prov = proveedor()
    if not prov:
        return False
    try:
        (_resend if prov == "resend" else _smtp)(destino, asunto, texto, cuerpo_html)
        return True
    except Exception:  # noqa: BLE001
        log.exception("No se pudo enviar el email de recuperacion")
        return False


def plantilla_recuperacion(nombre: str, enlace: str, minutos: int):
    """Devuelve (asunto, texto, html) del email de recuperacion."""
    asunto = "Recuperá tu contraseña de ResetPro"
    texto = (
        f"Hola {nombre},\n\n"
        f"Recibimos un pedido para crear una nueva contraseña. Entrá a este enlace (vale {minutos} minutos y se usa una sola vez):\n"
        f"{enlace}\n\n"
        "Si no fuiste vos, ignorá este mensaje: tu contraseña actual sigue funcionando."
    )
    n, e = html.escape(nombre), html.escape(enlace, quote=True)
    cuerpo = f"""<div style="background:#0B0B0C;padding:32px 16px;font-family:Arial,Helvetica,sans-serif">
  <div style="max-width:480px;margin:0 auto;background:#18181B;padding:32px;color:#F7F6F2">
    <h2 style="margin:0 0 16px;color:#F2A900">ResetPro</h2>
    <p style="margin:0 0 12px">Hola {n},</p>
    <p style="margin:0 0 24px;color:#C8C8CC">Recibimos un pedido para crear una nueva contraseña. El enlace vale {minutos} minutos y se usa una sola vez.</p>
    <p style="margin:0 0 24px"><a href="{e}" style="background:#F2A900;color:#0B0B0C;text-decoration:none;font-weight:bold;padding:14px 24px;display:inline-block">Crear nueva contraseña</a></p>
    <p style="margin:0;color:#9A9A9F;font-size:13px">Si no fuiste vos, ignorá este mensaje: tu contraseña actual sigue funcionando.</p>
  </div>
</div>"""
    return asunto, texto, cuerpo
