from typing import Dict, Any
from models import TaskProgress, TaskResult


class TaskManager:
    def __init__(self):
        self.storage: Dict[str, Dict[str, Any]] = {}

    def update_progress(self, task_id: str, status: str, percent: int):
        if task_id not in self.storage:
            self.storage[task_id] = {}
        progress = TaskProgress(status=status, percent=percent)
        self.storage[task_id].update(progress.dict())

    def get_progress(self, task_id: str) -> Dict[str, Any]:
        return self.storage.get(task_id, TaskProgress(status='Task not found', percent=0).dict())

    def set_results(self, task_id: str, results: Dict[str, Any]):
        if task_id not in self.storage:
            self.storage[task_id] = {}
        task_result = TaskResult(**results)
        self.storage[task_id]['results'] = task_result.dict()

    def get_results(self, task_id: str) -> Dict[str, Any]:
        return self.storage.get(task_id, {}).get('results', TaskResult().dict())
