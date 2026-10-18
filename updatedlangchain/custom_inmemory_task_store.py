import asyncio
from collections import OrderedDict
from datetime import datetime, timedelta
from typing import Optional
from a2a.server.tasks.task_store import TaskStore
from a2a.server.context import ServerCallContext
from a2a.types.a2a_pb2 import Task
from a2a.types.a2a_pb2 import ListTasksRequest, ListTasksResponse

import logging
from typing import Optional

# Configure logger
logger = logging.getLogger(__name__)

class CustomInMemoryTaskStore(TaskStore):
    """
    Custom in-memory TaskStore with LRU eviction and max tasks limit.
    """
    
    def __init__(
        self,
        max_tasks: int = 1000,
        task_ttl_seconds: Optional[int] = None,
        owner_resolver=None
    ):
        """
        Args:
            max_tasks: Maximum number of tasks to store. Evicts LRU when exceeded.
            task_ttl_seconds: Optional TTL in seconds for tasks. None = no TTL.
            owner_resolver: Optional function to resolve task owner from context.
        """
        self.max_tasks = max_tasks
        self.task_ttl = timedelta(seconds=task_ttl_seconds) if task_ttl_seconds else None
        self.owner_resolver = owner_resolver or (lambda ctx: "default")
        
        # OrderedDict maintains insertion order for LRU
        self._tasks: OrderedDict[str, dict] = OrderedDict()
        self._lock = asyncio.Lock()
        logger.info(
            "CustomInMemoryTaskStore initialized",
            extra={
                "max_tasks": max_tasks,
                "task_ttl_seconds": task_ttl_seconds
            }
        )
    
    async def _evict_if_needed(self):
        """Evict tasks if we exceed max_tasks or TTL expired."""
        now = datetime.now()
        
        # First, evict expired tasks (if TTL is set)
        if self.task_ttl:
            expired_ids = [
                task_id for task_id, data in self._tasks.items()
                if now - data["created_at"] > self.task_ttl
            ]
            for task_id in expired_ids:
                del self._tasks[task_id]
        
        # Then, evict LRU if we still exceed max_tasks
        while len(self._tasks) > self.max_tasks:
            # Pop oldest item (LRU)
            self._tasks.popitem(last=False)
    
    async def save(self, task: Task, context: ServerCallContext) -> None:
        """Save or update a task."""
        async with self._lock:
            task_id = task.id
            
            # Move to end (mark as recently used) if exists
            if task_id in self._tasks:
                self._tasks.move_to_end(task_id)
            
            # Store task with metadata
            self._tasks[task_id] = {
                "task": task,
                "created_at": datetime.now(),
                "last_accessed": datetime.now()
            }
            
            # Evict if needed
            await self._evict_if_needed()

            logger.info(
                f"Task saved: {task_id}",
                extra={
                    "task_id": task_id,
                    "is_update": task_id in self._tasks,
                    "total_tasks": len(self._tasks)
                }
            )
    
    async def get(self, task_id: str, context: ServerCallContext) -> Optional[Task]:
        """Retrieve a task by ID."""
        async with self._lock:
            if task_id not in self._tasks:
                return None
            
            # Update last accessed time and move to end (LRU)
            self._tasks[task_id]["last_accessed"] = datetime.now()
            self._tasks.move_to_end(task_id)
            
            return self._tasks[task_id]["task"]
    
    async def delete(self, task_id: str, context: ServerCallContext) -> None:
        """Delete a task by ID."""
        async with self._lock:
            if task_id in self._tasks:
                del self._tasks[task_id]
    
    async def list(
        self, 
        params: ListTasksRequest, 
        context: ServerCallContext
    ) -> ListTasksResponse:
        """List tasks based on request parameters."""
        async with self._lock:
            owner = self.owner_resolver(context)
            
            # Filter tasks by owner if needed
            tasks = []
            for task_id, data in self._tasks.items():
                task = data["task"]
                # Add your filtering logic here based on params
                # (status, created_after, etc.)
                tasks.append(task)
            
            # Apply pagination if needed
            page_size = params.page_size or 50
            page_token = params.page_token or 0
            
            start_idx = int(page_token)
            end_idx = start_idx + page_size
            paginated_tasks = tasks[start_idx:end_idx]
            
            return ListTasksResponse(
                tasks=paginated_tasks,
                next_page_token=str(end_idx) if end_idx < len(tasks) else None
            )