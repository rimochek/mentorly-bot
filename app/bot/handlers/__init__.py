from aiogram import Router

from app.bot.handlers import admin, profile, start, student, support, tutor


def setup_routers() -> Router:
    root = Router()
    root.include_router(start.router)
    root.include_router(support.router)
    root.include_router(profile.router)
    root.include_router(student.router)
    root.include_router(tutor.router)
    root.include_router(admin.router)
    return root
