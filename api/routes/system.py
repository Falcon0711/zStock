from fastapi import APIRouter
from services.background_tasks import get_task_queue

router = APIRouter(prefix="/api/system", tags=["系统管理"])

@router.get("/status")
def get_system_status():
    """获取系统状态和后台任务统计"""
    queue = get_task_queue()
    return {
        "background_tasks": queue.stats
    }
