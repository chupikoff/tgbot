from aiogram import Router
from .start import router as start_router
from .notes import router as notes_router
from .media import router as media_router
from .tasks import router as tasks_router
from .reminders import router as reminders_router
from .youtube import router as youtube_router
from .monitoring import router as monitoring_router
from .torrents import router as torrents_router
from .docker_containers import router as docker_router
from .backup import router as backup_router
from .users import router as users_router

router = Router()
router.include_router(start_router)
router.include_router(notes_router)
router.include_router(media_router)
router.include_router(tasks_router)
router.include_router(reminders_router)
router.include_router(youtube_router)
router.include_router(monitoring_router)
router.include_router(torrents_router)
router.include_router(docker_router)
router.include_router(backup_router)
router.include_router(users_router)
