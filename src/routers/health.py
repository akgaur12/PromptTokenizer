import os
import psutil
from fastapi import APIRouter
from src.core.config import get_settings

router = APIRouter(tags=["Health"])

_process = psutil.Process(os.getpid())


@router.get("/health")
def health_check():
    settings = get_settings()
    mem = _process.memory_info()
    
    return {
        "status": "ok",
        "service": settings.app_name,
        "version": settings.app_version,
        "memory": {
            "rss_mb": round(mem.rss / 1024 / 1024, 2),
            "vms_mb": round(mem.vms / 1024 / 1024, 2),
        },
    }
