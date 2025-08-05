from email.message import EmailMessage
import aiosmtplib
import os
from dotenv import load_dotenv

load_dotenv()


async def send_email(subject: str, to_whom: str, body: str, is_html: bool = False):
    message = EmailMessage()

    message["From"] = os.getenv("EMAIL_USERNAME")
    message["To"] = to_whom
    message["Subject"] = subject

    if is_html:
        message.set_content(
            "This is an HTML email. Please view in an HTML-compatible email client."
        )
        message.add_alternative(body, subtype="html")
    else:
        message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=os.getenv("EMAIL_HOST"),
        port=int(os.getenv("EMAIL_PORT")),
        start_tls=True,
        username=os.getenv("EMAIL_USERNAME"),
        password=os.getenv("EMAIL_PASSWORD"),
    )
