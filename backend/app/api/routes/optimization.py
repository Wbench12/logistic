# import uuid
# from typing import Any, List

# from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
# from sqlmodel import Session, select, func

# from app.api.deps import CurrentUser, SessionDep
# from app.models import (
#     OptimizationRequest,
#     OptimizationResult,
#     JobStatusResponse,
#     ValidationResult,
#     OptimizationJobsPublic,
#     OptimizationJobPublic,
#     Message,
#     OptimizationJob,
#     JobStatus,
# )
# from app.services.optimization import OptimizationService
# from app.services.validation import ValidationService
# from app.workers.tasks import solve_optimization_task

# router = APIRouter(prefix="/optimization", tags=["optimization"])


# @router.post("/validate", response_model=ValidationResult)
# def validate_optimization_data(
#     session: SessionDep,
#     current_user: CurrentUser,
#     request: OptimizationRequest,
# ) -> Any:
#     """
#     Validate optimization data before submission.
#     """
#     validation_service = ValidationService()
#     return validation_service.validate_request(request)


# @router.post("/optimize", response_model=Message)
# def submit_optimization_job(
#     session: SessionDep,
#     current_user: CurrentUser,
#     background_tasks: BackgroundTasks,
#     request: OptimizationRequest,
# ) -> Any:
#     """
#     Submit a new optimization job.
#     """
#     # Validate the request first
#     validation_service = ValidationService()
#     validation_result = validation_service.validate_request(request)
#     if not validation_result.is_valid:
#         raise HTTPException(
#             status_code=400,
#             detail={"errors": validation_result.errors, "warnings": validation_result.warnings},
#         )

#     # Create optimization job
#     job = OptimizationJob(
#         owner_id=current_user.id,
#         company_id=request.trips[0].company_id if request.trips else "default",
#         status=JobStatus.PENDING,
#         config=request.config.model_dump(),
#     )
#     session.add(job)
#     session.commit()
#     session.refresh(job)

#     # Store trip and vehicle data (in production, you might want to store this in the database)
#     # For now, we'll pass the data directly to the background task
    
#     # Start background task
#     background_tasks.add_task(
#         solve_optimization_task,
#         job_id=str(job.id),
#         request_data=request.model_dump()
#     )

#     return Message(message=f"Optimization job submitted with ID: {job.id}")


# @router.get("/status/{job_id}", response_model=JobStatusResponse)
# def get_job_status(
#     session: SessionDep,
#     current_user: CurrentUser,
#     job_id: uuid.UUID,
# ) -> Any:
#     """
#     Get the status of an optimization job.
#     """
#     job = session.get(OptimizationJob, job_id)
#     if not job:
#         raise HTTPException(status_code=404, detail="Job not found")
    
#     # Check permissions
#     if not current_user.is_superuser and job.owner_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Not enough permissions")

#     progress = 0.0
#     message = None
    
#     if job.status == JobStatus.RUNNING:
#         progress = 0.5
#         message = "Solver is running..."
#     elif job.status == JobStatus.COMPLETED:
#         progress = 1.0
#         message = "Optimization completed successfully"
#     elif job.status == JobStatus.INFEASIBLE:
#         progress = 1.0
#         message = "Problem is infeasible with current constraints"
#     elif job.status == JobStatus.FAILED:
#         progress = 1.0
#         message = "Optimization failed"

#     return JobStatusResponse(
#         job_id=job.id,
#         status=job.status,
#         progress=progress,
#         message=message,
#     )


# @router.get("/results/{job_id}", response_model=OptimizationResult)
# def get_job_results(
#     session: SessionDep,
#     current_user: CurrentUser,
#     job_id: uuid.UUID,
# ) -> Any:
#     """
#     Get the results of a completed optimization job.
#     """
#     job = session.get(OptimizationJob, job_id)
#     if not job:
#         raise HTTPException(status_code=404, detail="Job not found")
    
#     # Check permissions
#     if not current_user.is_superuser and job.owner_id != current_user.id:
#         raise HTTPException(status_code=403, detail="Not enough permissions")

#     if job.status not in [JobStatus.COMPLETED, JobStatus.INFEASIBLE]:
#         raise HTTPException(
#             status_code=400, 
#             detail=f"Job is not completed. Current status: {job.status}"
#         )

#     # Convert assignments to result format
#     assignments = []
#     for assignment in job.assignments:
#         # Group assignments by vehicle and build sequences
#         pass  # Implementation depends on how we store assignments

#     return OptimizationResult(
#         job_id=job.id,
#         status=job.status,
#         objective=job.objective,
#         metrics=job.metrics,
#         assignments=assignments,
#         diagnostics=job.diagnostics,
#     )


# @router.get("/jobs", response_model=OptimizationJobsPublic)
# def list_optimization_jobs(
#     session: SessionDep,
#     current_user: CurrentUser,
#     skip: int = 0,
#     limit: int = 100,
#     company_id: str = Query(None, description="Filter by company ID"),
# ) -> Any:
#     """
#     List optimization jobs for the current user.
#     """
#     if current_user.is_superuser:
#         count_statement = select(func.count()).select_from(OptimizationJob)
#         statement = select(OptimizationJob).offset(skip).limit(limit)
#     else:
#         count_statement = (
#             select(func.count())
#             .select_from(OptimizationJob)
#             .where(OptimizationJob.owner_id == current_user.id)
#         )
#         statement = (
#             select(OptimizationJob)
#             .where(OptimizationJob.owner_id == current_user.id)
#             .offset(skip)
#             .limit(limit)
#         )

#     if company_id:
#         count_statement = count_statement.where(OptimizationJob.company_id == company_id)
#         statement = statement.where(OptimizationJob.company_id == company_id)

#     count = session.exec(count_statement).one()
#     jobs = session.exec(statement).all()

#     public_jobs = [
#         OptimizationJobPublic(
#             id=job.id,
#             status=job.status,
#             objective=job.objective,
#             created_at=job.created_at,
#             updated_at=job.updated_at,
#             metrics=job.metrics,
#         )
#         for job in jobs
#     ]

#     return OptimizationJobsPublic(data=public_jobs, count=count)