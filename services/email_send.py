from email.message import EmailMessage
import aiosmtplib
import os
from dotenv import load_dotenv

load_dotenv()


async def send_email(subject: str, to_whom: str, body: str):
    message = EmailMessage()
    print(message)

    message["From"] = os.getenv("EMAIL_USERNAME")
    message["To"] = to_whom
    message["Subject"] = subject
    message.set_content(body)

    await aiosmtplib.send(
        message,
        hostname=os.getenv("EMAIL_HOST"),
        port=int(os.getenv("EMAIL_PORT")),
        start_tls=True,
        username=os.getenv("EMAIL_USERNAME"),
        password=os.getenv("EMAIL_PASSWORD"),
    )
