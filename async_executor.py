"""
Asynchronous task execution for background operations.
"""

import threading
import queue
import time
from typing import Dict, Optional, Callable, Any
from datetime import datetime
from enum import Enum


class TaskStatus(Enum):
    """Status of an async task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AsyncTask:
    """Represents an asynchronous task."""

    def __init__(self, task_id: str, goal: str, agent_runner: Callable):
        """
        Initialize async task.

        Args:
            task_id: Unique task identifier
            goal: Goal/description of the task
            agent_runner: Function to run the agent task
        """
        self.task_id = task_id
        self.goal = goal
        self.agent_runner = agent_runner
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.thread = None
        self.output_queue = queue.Queue()

    def run(self):
        """Execute the task."""
        self.status = TaskStatus.RUNNING
        self.start_time = datetime.now()

        try:
            self.result = self.agent_runner(self.goal, self.output_queue)
            self.status = TaskStatus.COMPLETED
        except Exception as e:
            self.error = str(e)
            self.status = TaskStatus.FAILED
        finally:
            self.end_time = datetime.now()

    def cancel(self):
        """Cancel the task (best effort)."""
        self.status = TaskStatus.CANCELLED

    def get_output(self) -> list:
        """Get accumulated output from task."""
        output = []
        while not self.output_queue.empty():
            try:
                output.append(self.output_queue.get_nowait())
            except queue.Empty:
                break
        return output

    def get_duration(self) -> Optional[float]:
        """Get task duration in seconds."""
        if self.start_time is None:
            return None
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()


class AsyncExecutor:
    """Manages asynchronous task execution."""

    def __init__(self, max_concurrent: int = 1):
        """
        Initialize async executor.

        Args:
            max_concurrent: Maximum concurrent tasks
        """
        self.max_concurrent = max_concurrent
        self.tasks: Dict[str, AsyncTask] = {}
        self.task_counter = 0

    def submit_task(self, goal: str, agent_runner: Callable) -> str:
        """
        Submit a task for async execution.

        Args:
            goal: Goal for the agent
            agent_runner: Function to run the agent

        Returns:
            Task ID
        """
        # Generate task ID
        self.task_counter += 1
        task_id = f"task_{self.task_counter}_{int(time.time())}"

        # Create task
        task = AsyncTask(task_id, goal, agent_runner)
        self.tasks[task_id] = task

        # Start task in background thread
        thread = threading.Thread(target=task.run, daemon=True)
        task.thread = thread
        thread.start()

        return task_id

    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """Get task by ID."""
        return self.tasks.get(task_id)

    def list_tasks(self) -> list:
        """List all tasks with their status."""
        return [{
            "id": task.task_id,
            "goal": task.goal,
            "status": task.status.value,
            "duration": task.get_duration(),
            "start_time": task.start_time.isoformat() if task.start_time else None
        } for task in self.tasks.values()]

    def get_running_tasks(self) -> list:
        """Get list of running tasks."""
        return [task for task in self.tasks.values() if task.status == TaskStatus.RUNNING]

    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task ID to cancel

        Returns:
            True if cancelled, False if not found or already finished
        """
        task = self.tasks.get(task_id)
        if task and task.status == TaskStatus.RUNNING:
            task.cancel()
            return True
        return False

    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> bool:
        """
        Wait for a task to complete.

        Args:
            task_id: Task ID to wait for
            timeout: Timeout in seconds (None = wait forever)

        Returns:
            True if completed, False if timeout
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.thread:
            task.thread.join(timeout=timeout)
            return not task.thread.is_alive()

        return True

    def cleanup_completed(self):
        """Remove completed tasks from memory."""
        completed = [
            task_id for task_id, task in self.tasks.items()
            if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]
        ]
        for task_id in completed:
            del self.tasks[task_id]

    def get_stats(self) -> Dict[str, Any]:
        """Get executor statistics."""
        return {
            "total_tasks": len(self.tasks),
            "pending": sum(1 for t in self.tasks.values() if t.status == TaskStatus.PENDING),
            "running": sum(1 for t in self.tasks.values() if t.status == TaskStatus.RUNNING),
            "completed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.COMPLETED),
            "failed": sum(1 for t in self.tasks.values() if t.status == TaskStatus.FAILED),
            "cancelled": sum(1 for t in self.tasks.values() if t.status == TaskStatus.CANCELLED),
        }
