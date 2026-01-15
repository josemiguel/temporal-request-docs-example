from datetime import timedelta
from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from activities import validate_document
    from models import DocumentType, DocumentValidation, DocumentStatus


@workflow.defn
class DocumentRequestWorkflow:
    """Workflow for requesting and validating 3 documents with human interaction."""

    def __init__(self) -> None:
        self._document_status = DocumentStatus()
        self._status = "Waiting for documents"
        self._completed = False
        self._pending_submissions: list[tuple[str, str]] = []

    @workflow.signal
    async def submit_document(self, document_type: str, content: str) -> None:
        """Signal to submit a document for validation."""
        workflow.logger.info(f"Received document submission: {document_type}")
        self._pending_submissions.append((document_type, content))

    @workflow.query
    def get_status(self) -> dict:
        """Query to get current workflow status."""
        return {
            "status": self._status,
            "documents": self._document_status.to_dict(),
            "all_valid": self._document_status.all_valid(),
            "completed": self._completed,
        }

    @workflow.run
    async def run(self, request_id: str) -> dict:
        """
        Main workflow execution.
        Waits for 3 valid documents with a 7-day timeout.
        """
        workflow.logger.info(f"Starting document request workflow: {request_id}")
        self._status = "Waiting for documents"

        # Wait for all documents to be valid or timeout after 7 days
        try:
            await workflow.wait_condition(
                lambda: self._document_status.all_valid(),
                timeout=timedelta(days=7),
            )
        except TimeoutError:
            self._status = "Timed out - 7 days elapsed"
            self._completed = True
            return {
                "status": "timeout",
                "message": "Document request timed out after 7 days",
                "documents": self._document_status.to_dict(),
            }

        # All documents are valid
        self._status = "All documents validated successfully"
        self._completed = True
        workflow.logger.info("All documents validated successfully!")

        return {
            "status": "completed",
            "message": "All documents have been validated successfully",
            "documents": self._document_status.to_dict(),
        }

    @workflow.signal
    async def process_submission(self, document_type: str, content: str) -> None:
        """Process a document submission by validating it."""
        workflow.logger.info(f"Processing document: {document_type}")

        # Validate the document using the activity
        result = await workflow.execute_activity(
            validate_document,
            args=[document_type, content],
            start_to_close_timeout=timedelta(seconds=60),
        )

        validation = DocumentValidation(
            document_type=DocumentType(result["document_type"]),
            is_valid=result["is_valid"],
            message=result["message"],
        )

        # Update the appropriate document status
        if validation.document_type == DocumentType.FULL_NAME:
            self._document_status.full_name = validation
        elif validation.document_type == DocumentType.PASSPORT:
            self._document_status.passport = validation
        elif validation.document_type == DocumentType.ADDRESS:
            self._document_status.address = validation

        if self._document_status.all_valid():
            self._status = "All documents validated successfully"
        else:
            self._status = "Waiting for valid documents"

        workflow.logger.info(f"Document validation result: {validation.is_valid} - {validation.message}")
