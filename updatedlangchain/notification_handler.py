# notification_handler.py
import logging
from typing import Callable
from a2a.types.a2a_pb2 import Task

logger = logging.getLogger(__name__)

class NotificationHandler:
    def __init__(self):
        self.callbacks = {}
    
    def register_callback(self, task_id: str, callback: Callable):
        """Register a callback for a specific task"""
        self.callbacks[task_id] = callback
    
    async def notify(self, task: Task):
        """Send notification when task status changes"""
        task_id = task.id
        if task_id in self.callbacks:
            try:
                await self.callbacks[task_id](task)
                logger.info(f"Notification sent for task {task_id}")
            except Exception as e:
                logger.error(f"Failed to send notification for task {task_id}: {e}")