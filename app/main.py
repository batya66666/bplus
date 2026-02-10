from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi import Request
from app.routers import auth, users, courses, standups, documents, departments
from app.routers import my_courses
from app.settings import settings
from app.routers import auth, users, courses, standups, documents

app = FastAPI(title="Internal LMS API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ фронт
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")

app.include_router(departments.router, prefix="/departments", tags=["departments"])

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


app.include_router(auth.router, prefix="/auth", tags=["auth"])
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(courses.router, prefix="/courses", tags=["courses"])
app.include_router(standups.router, prefix="/standups", tags=["standups"])
app.include_router(documents.router, prefix="/documents", tags=["documents"])
app.include_router(my_courses.router, prefix="/my-courses", tags=["my-courses"])

@app.get("/health")
async def health():
    return {"status": "ok", "env": settings.app_env}
