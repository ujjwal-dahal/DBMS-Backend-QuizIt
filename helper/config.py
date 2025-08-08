from dotenv import load_dotenv
import os

load_dotenv()

# Fernet
FERNET_KEY = os.getenv("ENCRYPTION_KEY")
ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

# Authentication Google
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY")
SERVICE_METADATA_URL = os.getenv("SERVICE_METADATA_URL")

# JWT Authentication
TOKEN_SECRET = os.getenv("TOKEN_SECRET")
TOKEN_ALGO = os.getenv("TOKEN_ALGO")
ALGORITHM = os.getenv("JWT_ALGORITHM")
SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM")

# JWT Time
ACCESS_TOKEN_EXPIRY = 120  # 120 Minutes
REFRESH_TOKEN_EXPIRY = 1  # 1 Days

# Email & Password Expiry Time
VERIFY_MAIL_EXPIRY = 5
FORGOT_PASSWORD_EXPIRY = 5

# Default Quiz Cover Photo
DEFAULT_COVER_PHOTO_URL = os.getenv("DEFAULT_COVER_PHOTO_URL")

# QuizIt URL
QUIZIT_URL = os.getenv("QUIZIT_URL")
ANOTHER_URL = os.getenv("ANOTHER_URL", "http://localhost:8081")
