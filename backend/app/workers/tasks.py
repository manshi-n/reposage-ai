"""
Celery tasks. Keeps repository analysis off the request/response cycle
of the FastAPI process, per the spec's background-processing section.
"""
from app.core.database import SessionLocal
from app.models.models import Analysis, Repository
from app.services.analysis_service import run_analysis
from app.services.progress_service import push_progress
from app.workers.celery_app import celery_app


@celery_app.task(name="app.workers.tasks.run_analysis_task", bind=True, max_retries=0)
def run_analysis_task(self, analysis_id: str) -> None:
    db = SessionLocal()
    try:
        analysis = db.query(Analysis).filter(Analysis.id == analysis_id).first()
        if not analysis:
            return
        repository = db.query(Repository).filter(Repository.id == analysis.repository_id).first()
        if not repository:
            analysis.status = "failed"
            analysis.error_message = "Repository not found."
            db.commit()
            push_progress(analysis_id, "failed", 0, error_message="Repository not found.")
            return

        def progress_callback(status, percent: int) -> None:
            status_value = status.value if hasattr(status, "value") else status
            push_progress(analysis_id, status_value, percent)

        run_analysis(db, analysis, clone_url=repository.clone_url, progress_cb=progress_callback)
    finally:
        db.close()