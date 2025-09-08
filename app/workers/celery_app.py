from celery import Celery
import os
import sys

# Add the parent directory to the path - ИСПРАВЛЕНО
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from app.config.settings import settings

# Create Celery app
celery_app = Celery(
    'agatha',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['app.workers.tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Task routing
celery_app.conf.task_routes = {
    'app.workers.tasks.process_llm_request': {'queue': 'llm'},
    'app.workers.tasks.process_asr_request': {'queue': 'asr'},
    'app.workers.tasks.process_vision_request': {'queue': 'vision'},
    'app.workers.tasks.generate_summary': {'queue': 'summary'},
}

if __name__ == '__main__':
    celery_app.start() 