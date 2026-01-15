"""
Celery worker configuration for OmniSense
Run with: celery -A celery_worker worker --loglevel=info
"""

from api import celery_app

if __name__ == "__main__":
    celery_app.start()
