"""
mail_agent.py — Email sending for BlackBugsAI

Supports: SMTP (any provider), Gmail OAuth2 (optional)
Config via .env:
  MAIL_HOST=smtp.gmail.com
  MAIL_PORT=587
  MAIL_USER=your@email.com
  MAIL_PASS=app_password
  MAIL_FROM=BlackBugsAI <your@email.com>   # optional display name
  MAIL_TLS=true                             # STARTTLS (default)
  MAIL_SSL=false                            # direct SSL (port 465)

Usage:
  from mail_agent import send_mail, MailMessage
  ok, err = send_mail(to="user@example.com", subject="Hi", body="Hello!")
"""
from __future__ import annotations
import os, smtplib, ssl, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from dataclasses import dataclass, field
from typing import List, Optional
import config as _cfg

@dataclass
class MailMessage:
    to:          str | List[str]
    subject:     str
    body:        str
    html:        str              = ""
    cc:          List[str]        = field(default_factory=list)
    bcc:         List[str]        = field(default_factory=list)
    attachments: List[str]        = field(default_factory=list)  # file paths
    reply_to:    str              = ""


def _get_cfg() -> dict:
    return {
        "host":  os.environ.get("MAIL_HOST", ""),
        "port":  int(os.environ.get("MAIL_PORT", "587") or "587"),
        "user":  os.environ.get("MAIL_USER", ""),
        "pwd":   os.environ.get("MAIL_PASS", ""),
        "from":  os.environ.get("MAIL_FROM", "") or os.environ.get("MAIL_USER", ""),
        "tls":   os.environ.get("MAIL_TLS", "true").lower() != "false",
        "ssl":   os.environ.get("MAIL_SSL", "false").lower() == "true",
    }


def is_configured() -> bool:
    """Returns True if SMTP credentials are set."""
    cfg = _get_cfg()
    return bool(cfg["host"] and cfg["user"] and cfg["pwd"])


def send_mail(to: str | List[str],
              subject: str,
              body: str,
              html: str = "",
              attachments: List[str] | None = None,
              cc: List[str] | None = None,
              reply_to: str = "") -> tuple[bool, str]:
    """
    Send an email. Returns (ok: bool, message: str).

    Examples:
        send_mail("user@example.com", "Hello", "Plain text body")
        send_mail(["a@b.com","c@d.com"], "Report", "See attachment",
                  attachments=["/tmp/report.pdf"])
    """
    if not is_configured():
        return False, "SMTP not configured. Set MAIL_HOST, MAIL_USER, MAIL_PASS in .env"

    msg = MailMessage(
        to=to, subject=subject, body=body, html=html,
        cc=cc or [], bcc=[], attachments=attachments or [],
        reply_to=reply_to,
    )
    return _send(msg)


def _build_mime(msg: MailMessage, from_addr: str) -> MIMEMultipart:
    mime = MIMEMultipart("alternative" if msg.html else "mixed")
    to_list = [msg.to] if isinstance(msg.to, str) else list(msg.to)
    mime["From"]    = from_addr
    mime["To"]      = ", ".join(to_list)
    mime["Subject"] = msg.subject
    if msg.cc:
        mime["Cc"] = ", ".join(msg.cc)
    if msg.reply_to:
        mime["Reply-To"] = msg.reply_to

    mime.attach(MIMEText(msg.body, "plain", "utf-8"))
    if msg.html:
        mime.attach(MIMEText(msg.html, "html", "utf-8"))

    for path in msg.attachments:
        if not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
            encoders.encode_base64(part)
            filename = os.path.basename(path)
            part.add_header("Content-Disposition", f"attachment; filename={filename}")
            mime.attach(part)
        except Exception:
            pass
    return mime


def _send(msg: MailMessage) -> tuple[bool, str]:
    cfg = _get_cfg()
    from_addr = cfg["from"] or cfg["user"]
    mime      = _build_mime(msg, from_addr)

    to_list = [msg.to] if isinstance(msg.to, str) else list(msg.to)
    all_rcpt = to_list + msg.cc + msg.bcc

    try:
        ctx = ssl.create_default_context()
        if cfg["ssl"]:
            with smtplib.SMTP_SSL(cfg["host"], cfg["port"], context=ctx) as server:
                server.login(cfg["user"], cfg["pwd"])
                server.sendmail(from_addr, all_rcpt, mime.as_string())
        else:
            with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
                server.ehlo()
                if cfg["tls"]:
                    server.starttls(context=ctx)
                    server.ehlo()
                server.login(cfg["user"], cfg["pwd"])
                server.sendmail(from_addr, all_rcpt, mime.as_string())

        recipients_str = ", ".join(all_rcpt[:3])
        if len(all_rcpt) > 3:
            recipients_str += f" (+{len(all_rcpt)-3})"
        return True, f"Sent to {recipients_str}"

    except smtplib.SMTPAuthenticationError:
        return False, "SMTP auth failed — check MAIL_USER / MAIL_PASS"
    except smtplib.SMTPConnectError as e:
        return False, f"SMTP connect failed ({cfg['host']}:{cfg['port']}): {e}"
    except Exception as e:
        return False, str(e)


def send_admin_notification(subject: str, body: str,
                            admin_email: str = "") -> tuple[bool, str]:
    """Send notification to admin email (ADMIN_EMAIL or GOD_EMAIL in .env)."""
    to = (admin_email
          or os.environ.get("ADMIN_EMAIL", "")
          or os.environ.get("GOD_EMAIL", ""))
    if not to:
        return False, "ADMIN_EMAIL not set in .env"
    return send_mail(to, subject, body)


def mail_status() -> str:
    """HTML status for admin panel."""
    cfg = _get_cfg()
    if not is_configured():
        return "📧 Mail: <b>не настроен</b> (нет MAIL_HOST/USER/PASS в .env)"
    tls_info = "SSL" if cfg["ssl"] else ("STARTTLS" if cfg["tls"] else "plain")
    return (
        f"📧 Mail: <b>настроен</b>\n"
        f"  Host: <code>{cfg['host']}:{cfg['port']}</code> ({tls_info})\n"
        f"  From: <code>{cfg['from']}</code>"
    )
