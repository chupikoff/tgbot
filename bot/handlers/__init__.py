from aiogram import Router
from .start import router as start_router
from .admin import router as admin_router
from .monitoring import router as monitoring_router
from .notes import router as notes_router
from .torrents import router as torrents_router
from .backup import router as backup_router
from .media import router as media_router
from .services import router as services_router

router = Router()
router.include_router(start_router)
router.include_router(admin_router)
router.include_router(monitoring_router)
router.include_router(notes_router)
router.include_router(torrents_router)
router.include_router(backup_router)
router.include_router(media_router)
router.include_router(services_router)
