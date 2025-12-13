"""
后台任务队列（带优先级和去重）
使用 threading 实现异步任务处理
"""

import threading
import queue
import time
from typing import Callable, Optional
from enum import IntEnum
from utils.logger import get_logger

logger = get_logger(__name__)


class TaskPriority(IntEnum):
    """任务优先级（数字越小优先级越高）"""
    HIGH = 1      # 增量更新（用户立即需要）
    NORMAL = 5    # 普通任务
    LOW = 10      # 历史补全（后台慢慢做）


class BackgroundTaskQueue:
    """后台任务队列（带优先级和去重）"""
    
    def __init__(self, num_workers: int = 2):
        """
        初始化任务队列
        
        Args:
            num_workers: 工作线程数量
        """
        # 使用优先级队列
        self._queue = queue.PriorityQueue()
        self._workers = []
        self._running = True
        self._num_workers = num_workers
        self._pending_tasks = set()  # 用于任务去重
        self._lock = threading.Lock()  # 保护 pending_tasks
        self._task_counter = 0  # 用于保持相同优先级任务的 FIFO 顺序
        
        # 统计信息
        self._completed_count = 0
        self._failed_count = 0
        
        # 启动工作线程
        for i in range(num_workers):
            worker = threading.Thread(
                target=self._worker,
                name=f"BackgroundWorker-{i}",
                daemon=True
            )
            worker.start()
            self._workers.append(worker)
        
        logger.info(f"后台任务队列已启动，工作线程数: {num_workers}")
    
    def _worker(self):
        """工作线程主循环"""
        worker_name = threading.current_thread().name
        
        while self._running:
            try:
                # 从优先级队列获取任务（超时1秒）
                try:
                    priority, counter, task_data = self._queue.get(timeout=1)
                except queue.Empty:
                    continue
                
                if task_data is None:
                    continue
                
                task_name, func, args, kwargs = task_data
                
                try:
                    logger.info(f"[{worker_name}] 开始执行任务: {task_name} (优先级: {priority})")
                    start_time = time.time()
                    
                    func(*args, **kwargs)
                    
                    elapsed = time.time() - start_time
                    self._completed_count += 1
                    logger.info(f"[{worker_name}] 任务完成: {task_name} (耗时 {elapsed:.2f}s)")
                    
                except Exception as e:
                    self._failed_count += 1
                    logger.error(f"[{worker_name}] 任务执行失败: {task_name} - {e}", exc_info=True)
                
                finally:
                    # 任务完成后从 pending 集合中移除
                    with self._lock:
                        self._pending_tasks.discard(task_name)
                    self._queue.task_done()
                    
            except Exception as e:
                logger.error(f"[{worker_name}] 工作线程异常: {e}")
    
    def submit(
        self, 
        func: Callable, 
        *args, 
        task_name: Optional[str] = None, 
        priority: TaskPriority = TaskPriority.NORMAL,
        **kwargs
    ):
        """
        提交任务到队列（带优先级和去重）
        
        Args:
            func: 要执行的函数
            task_name: 任务名称（用于日志和去重）
            priority: 任务优先级
            *args: 函数参数
            **kwargs: 函数关键字参数
        """
        if task_name is None:
            task_name = func.__name__
        
        # 检查是否已有相同任务在队列或执行中
        with self._lock:
            if task_name in self._pending_tasks:
                logger.debug(f"任务已在队列中，跳过: {task_name}")
                return
            self._pending_tasks.add(task_name)
            self._task_counter += 1
            counter = self._task_counter
        
        # 优先级队列需要 (priority, counter, data) 格式
        task_data = (task_name, func, args, kwargs)
        self._queue.put((priority, counter, task_data))
        logger.debug(f"任务已提交: {task_name} (优先级: {priority}, 队列大小: {self._queue.qsize()})")
    
    def wait_completion(self, timeout: Optional[float] = None):
        """等待所有任务完成"""
        self._queue.join()
    
    def shutdown(self):
        """关闭任务队列"""
        logger.info("正在关闭后台任务队列...")
        self._running = False
        for worker in self._workers:
            worker.join(timeout=5)
        logger.info("后台任务队列已关闭")
    
    @property
    def queue_size(self) -> int:
        """获取当前队列大小"""
        return self._queue.qsize()
    
    @property
    def stats(self) -> dict:
        """获取统计信息"""
        return {
            "queue_size": self._queue.qsize(),
            "pending_tasks": len(self._pending_tasks),
            "completed": self._completed_count,
            "failed": self._failed_count,
            "workers": self._num_workers
        }


# 全局单例
_task_queue: Optional[BackgroundTaskQueue] = None


def get_task_queue() -> BackgroundTaskQueue:
    """获取全局任务队列实例"""
    global _task_queue
    
    if _task_queue is None:
        try:
            from services.data_config import BACKGROUND_WORKERS
            num_workers = BACKGROUND_WORKERS
        except (ImportError, AttributeError):
            num_workers = 2
        
        _task_queue = BackgroundTaskQueue(num_workers=num_workers)
    
    return _task_queue


def submit_background_task(
    func: Callable, 
    *args, 
    task_name: Optional[str] = None, 
    priority: TaskPriority = TaskPriority.NORMAL,
    **kwargs
):
    """
    提交后台任务（便捷函数）
    
    Args:
        func: 要执行的函数
        task_name: 任务名称
        priority: 任务优先级 (HIGH=1, NORMAL=5, LOW=10)
        *args: 函数参数
        **kwargs: 函数关键字参数
    """
    queue = get_task_queue()
    queue.submit(func, *args, task_name=task_name, priority=priority, **kwargs)
