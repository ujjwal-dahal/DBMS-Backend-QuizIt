import cloudinary
from dotenv import load_dotenv
import os

load_dotenv()


def configure_cloudinary():
    cloud_name = os.getenv("CLOUD_NAME")
    api_key = os.getenv("API_KEY")
    api_secret = os.getenv("API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        raise ValueError("Cloudinary environment variables not set properly.")

    cloudinary.config(
        cloud_name=cloud_name,
        api_key=api_key,
        api_secret=api_secret,
    )


configure_cloudinary()
