# FastAPI Imports
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware


# Projects Import
from app.authentication.main import app as auth_router
from app.users.main import router as user_router
from app.quiz.main import app as quiz_app
from app.websocket.main import app as websocket_app
from app.features.main import app as features_app
from helper.config import (
    QUIZIT_URL,
    ANOTHER_URL,
    AUTH_SECRET_KEY,
)

app = FastAPI()


app.add_middleware(SessionMiddleware, secret_key=AUTH_SECRET_KEY)


templates = Jinja2Templates(directory="api/templates")


@app.get("/", response_class=HTMLResponse, tags=["Index"])
def index_page(request: Request):
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "message": "QuizIt API",
            "backend": "Ujjwal Dahal",
            "frontend": "Dharmananda Joshi",
        },
    )


app.include_router(auth_router, prefix="/auth", tags=["Authentication"])
app.include_router(quiz_app, prefix="/quiz", tags=["Quiz"])
app.include_router(user_router, prefix="/user", tags=["User"])
app.include_router(websocket_app, prefix="/room", tags=["WebSocket"])
app.include_router(features_app, tags=["Features"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=[QUIZIT_URL, ANOTHER_URL],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/check-auth", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("check_auth.html", {"request": request})
