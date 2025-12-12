# import uuid
# from typing import Dict, Any, Optional, List

# from celery import Celery
# from celery.app.base import Celery as CeleryAppType
# from celery.app.task import Task as CeleryTaskType
# from sqlmodel import Session
# import sqlmodel  # Added to fix NameError for sqlmodel
# import os

# from app.core.config import settings
# from app.core.db import engine
# from app.models import OptimizationJob, JobStatus, Assignment, Trip, Vehicle
# from app.services.optimization import OptimizationService


# # Use environment variables or fallback to default Redis URL
# CELERY_BROKER_URL: str = getattr(settings, "CELERY_BROKER_URL", None) or os.environ.get("CELERY_BROKER_URL") or "redis://localhost:6379/0"
# CELERY_RESULT_BACKEND: str = getattr(settings, "CELERY_RESULT_BACKEND", None) or os.environ.get("CELERY_RESULT_BACKEND") or "redis://localhost:6379/0"


# celery_app: CeleryAppType = Celery(
#     "logistics_worker",
#     broker=CELERY_BROKER_URL,
#     backend=CELERY_RESULT_BACKEND,
# )

# celery_app.conf.update(
#     task_serializer="json",
#     accept_serializer="json",
#     result_serializer="json",
#     timezone="UTC",
#     enable_utc=True,
# )


# @celery_app.task(bind=True)
# def solve_optimization_task(
#     self: CeleryTaskType,
#     job_id: str,
#     request_data: Dict[str, Any]
# ) -> None:
#     """
#     Celery task to solve optimization problem in background.
#     """
#     job: Optional[OptimizationJob] = None
#     result: Any
#     assignment_result: Any
#     assignment: Optional[Assignment]
#     idx: int
#     trip_id: str
#     start_time: int
#     is_last: bool
#     # Session context
#     with Session(engine) as session:
#         try:
#             # Get the job
#             job = session.get(OptimizationJob, uuid.UUID(job_id))
#             if not job:
#                 self.update_state(state='FAILED', meta={'error': 'Job not found'})
#                 return
            
#             # Update status to running
#             job.status = JobStatus.RUNNING
#             session.add(job)
#             session.commit()
            
#             # Solve the optimization problem
#             optimization_service = OptimizationService()
#             result = optimization_service.solve_optimization(request_data)
            
#             # Update job with results
#             job.status = result.status
#             job.objective = result.objective
#             job.metrics = result.metrics
#             job.diagnostics = result.diagnostics
            
#             # Store assignments in database
#             if result.status == JobStatus.COMPLETED and result.assignments:
#                 for assignment_result in result.assignments:
#                     for idx, (trip_id, start_time, is_last) in enumerate(zip(
#                         assignment_result.trip_sequence,
#                         assignment_result.start_times,
#                         assignment_result.is_last
#                     )):
#                         assignment = Assignment(
#                             job_id=job.id,
#                             vehicle_id=assignment_result.vehicle_id,
#                             trip_id=uuid.UUID(trip_id),
#                             sequence_order=idx,
#                             start_time=start_time,
#                             end_time=start_time + 60,  # Would use actual duration
#                             is_last=is_last
#                         )
#                         session.add(assignment)
            
#             session.add(job)
#             session.commit()
            
#             self.update_state(
#                 state='SUCCESS',
#                 meta={
#                     'job_id': str(job.id),
#                     'status': job.status.value,
#                     'objective': job.objective,
#                     'assignments_count': len(result.assignments) if result.assignments else 0
#                 }
#             )
            
#         except Exception as e:
#             # Mark job as failed
#             if 'job' in locals() and job is not None:
#                 job.status = JobStatus.FAILED
#                 job.diagnostics = [f"Optimization failed: {str(e)}"]
#                 session.add(job)
#                 session.commit()
            
#             self.update_state(
#                 state='FAILED',
#                 meta={'error': str(e)}
#             )
#             raise