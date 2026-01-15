import asyncio
import uuid
from contextlib import asynccontextmanager
from multiprocessing import Process

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from temporalio.client import Client
from temporalio.worker import Worker

from activities import validate_document
from workflow import DocumentRequestWorkflow

TASK_QUEUE = "document-request-queue"
TEMPORAL_HOST = "localhost:7233"


def run_worker():
    """Run the Temporal worker in a separate process."""
    import asyncio
    from dotenv import load_dotenv
    load_dotenv()

    async def worker_main():
        client = await Client.connect(TEMPORAL_HOST)
        worker = Worker(
            client,
            task_queue=TASK_QUEUE,
            workflows=[DocumentRequestWorkflow],
            activities=[validate_document],
        )
        print(f"Worker started, listening on task queue: {TASK_QUEUE}")
        await worker.run()

    asyncio.run(worker_main())


worker_process: Process | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the Temporal worker lifecycle."""
    global worker_process

    # Start worker in a separate process
    worker_process = Process(target=run_worker, daemon=True)
    worker_process.start()
    print("Temporal worker process started")

    yield

    # Cleanup
    if worker_process and worker_process.is_alive():
        worker_process.terminate()
        worker_process.join(timeout=5)
        print("Temporal worker process stopped")


app = FastAPI(title="Document Request API", lifespan=lifespan)


# Request models
class StartWorkflowRequest(BaseModel):
    request_id: str | None = None


class SubmitDocumentRequest(BaseModel):
    workflow_id: str
    document_type: str  # "full_name", "passport", "address"
    content: str


class WorkflowStatusRequest(BaseModel):
    workflow_id: str


# API Endpoints
@app.get("/")
async def serve_frontend():
    """Serve the frontend HTML."""
    return FileResponse("index.html")


@app.post("/api/workflow/start")
async def start_workflow(request: StartWorkflowRequest):
    """Start a new document request workflow."""
    try:
        client = await Client.connect(TEMPORAL_HOST)
        workflow_id = request.request_id or f"doc-request-{uuid.uuid4()}"

        handle = await client.start_workflow(
            DocumentRequestWorkflow.run,
            workflow_id,
            id=workflow_id,
            task_queue=TASK_QUEUE,
        )

        return JSONResponse(
            {
                "success": True,
                "workflow_id": handle.id,
                "message": "Document request workflow started",
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/document/submit")
async def submit_document(request: SubmitDocumentRequest):
    """Submit a document to an existing workflow."""
    try:
        client = await Client.connect(TEMPORAL_HOST)
        handle = client.get_workflow_handle(request.workflow_id)

        # Send signal to process the document submission
        await handle.signal(
            DocumentRequestWorkflow.process_submission,
            args=[request.document_type, request.content],
        )

        # Wait a moment for processing, then get status
        await asyncio.sleep(1)

        status = await handle.query(DocumentRequestWorkflow.get_status)

        return JSONResponse(
            {
                "success": True,
                "message": f"Document '{request.document_type}' submitted for validation",
                "status": status,
            }
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflow/{workflow_id}/status")
async def get_workflow_status(workflow_id: str):
    """Get the current status of a workflow."""
    try:
        client = await Client.connect(TEMPORAL_HOST)
        handle = client.get_workflow_handle(workflow_id)
        status = await handle.query(DocumentRequestWorkflow.get_status)

        return JSONResponse({"success": True, "status": status})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/workflows")
async def list_workflows():
    """List all document request workflows."""
    try:
        client = await Client.connect(TEMPORAL_HOST)
        workflows = []
        
        async for workflow in client.list_workflows(
            query="WorkflowType = 'DocumentRequestWorkflow'"
        ):
            workflow_status = "Unknown"
            if workflow.status.name == "RUNNING":
                workflow_status = "Running"
            elif workflow.status.name == "COMPLETED":
                workflow_status = "Completed"
            elif workflow.status.name == "FAILED":
                workflow_status = "Failed"
            elif workflow.status.name == "CANCELED":
                workflow_status = "Canceled"
            elif workflow.status.name == "TERMINATED":
                workflow_status = "Terminated"
            elif workflow.status.name == "TIMED_OUT":
                workflow_status = "Timed Out"
            
            workflows.append({
                "workflow_id": workflow.id,
                "status": workflow_status,
                "start_time": workflow.start_time.isoformat() if workflow.start_time else None,
            })
        
        # Sort by start_time descending (newest first)
        workflows.sort(key=lambda x: x["start_time"] or "", reverse=True)
        
        return JSONResponse({"success": True, "workflows": workflows})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
