"""
Email sender for List-Sync reports
Based on proc-watchdog sendmail.py pattern
"""

import os
import smtplib
import ssl
import time
from email.message import EmailMessage
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


def _outbox_dir():
    """Get outbox directory for saving emails when SMTP not configured"""
    from ..utils.logger import DATA_DIR
    d = Path(DATA_DIR) / "reports" / "outbox"
    d.mkdir(parents=True, exist_ok=True)
    return d


def send_email(subject: str, body: str, html: bool = True, pdf_attachment: bytes = None, pdf_filename: str = "report.pdf"):
    """
    Send email via SMTP or save to outbox
    
    Args:
        subject: Email subject
        body: Email body (plain text or HTML)
        html: Whether body is HTML
        pdf_attachment: Optional PDF file content as bytes
        pdf_filename: Filename for PDF attachment
        
    Returns:
        str: "sent" if emailed, file path if saved to outbox
    """
    # Get SMTP configuration from environment
    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587") or "587")
    user = os.getenv("SMTP_USER", "")
    password = os.getenv("SMTP_PASSWORD", "")
    starttls = str(os.getenv("SMTP_STARTTLS", "1")).lower() in ("1", "true", "yes", "on")
    mail_from = os.getenv("MAIL_FROM", "list-sync@example.local")
    mail_to = os.getenv("MAIL_TO", "")
    
    if not mail_to:
        logger.warning("MAIL_TO not configured, email reports disabled")
        return None
    
    # If no SMTP host, save to outbox instead
    if not host:
        logger.info("SMTP not configured, saving email to outbox")
        ts = time.strftime("%Y%m%d-%H%M%S")
        safe_subject = subject.replace(' ', '_').replace('/', '-')[:50]
        fn = _outbox_dir() / f"{ts}-{safe_subject}.eml"
        
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = mail_from
        msg["To"] = mail_to
        
        if html and ("<html" in body.lower() or "<!doctype" in body.lower()):
            msg.set_content("HTML report attached.")
            msg.add_alternative(body, subtype="html")
        else:
            msg.set_content(body)
        
        # Attach PDF if provided
        if pdf_attachment:
            msg.add_attachment(
                pdf_attachment,
                maintype='application',
                subtype='pdf',
                filename=pdf_filename
            )
            logger.info(f"Attached PDF: {pdf_filename} ({len(pdf_attachment)} bytes)")
        
        with open(fn, "wb") as f:
            f.write(bytes(msg))
        
        logger.info(f"Email saved to: {fn}")
        return str(fn)
    
    # Send via SMTP
    try:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = mail_from
        msg["To"] = mail_to
        
        if html and ("<html" in body.lower() or "<!doctype" in body.lower()):
            msg.set_content("HTML report - please view in HTML-capable email client.")
            msg.add_alternative(body, subtype="html")
        else:
            msg.set_content(body)
        
        # Attach PDF if provided
        if pdf_attachment:
            msg.add_attachment(
                pdf_attachment,
                maintype='application',
                subtype='pdf',
                filename=pdf_filename
            )
            logger.info(f"Attached PDF: {pdf_filename} ({len(pdf_attachment)} bytes)")
        
        if starttls:
            context = ssl.create_default_context()
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                server.starttls(context=context)
                server.ehlo()
                if user:
                    server.login(user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                if user:
                    server.login(user, password)
                server.send_message(msg)
        
        logger.info(f"Email sent to: {mail_to}")
        return "sent"
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        # Save to outbox as fallback
        ts = time.strftime("%Y%m%d-%H%M%S")
        safe_subject = subject.replace(' ', '_').replace('/', '-')[:50]
        fn = _outbox_dir() / f"{ts}-{safe_subject}-failed.eml"
        
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = mail_from
        msg["To"] = mail_to
        msg.set_content(f"Failed to send: {e}\n\n{body}")
        
        with open(fn, "wb") as f:
            f.write(bytes(msg))
        
        logger.error(f"Email send failed, saved to: {fn}")
        return str(fn)

