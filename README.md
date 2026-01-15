# Document Verification Portal

A durable document verification system built with **Temporal**, **FastAPI**, and **Vue.js**. This application demonstrates human-in-the-loop workflows where users submit identity documents that are validated using **Google Gemini AI**.

![Document Verification](https://img.shields.io/badge/Temporal-Workflow-blue) ![FastAPI](https://img.shields.io/badge/FastAPI-Backend-green) ![Vue.js](https://img.shields.io/badge/Vue.js-Frontend-brightgreen)

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Installation](#installation)
  - [1. Install Temporal CLI](#1-install-temporal-cli)
  - [2. Install Python Dependencies](#2-install-python-dependencies)
  - [3. Configure Environment Variables](#3-configure-environment-variables)
- [Running the Application](#running-the-application)
- [How the Workflow Works](#how-the-workflow-works)
  - [Workflow Overview](#workflow-overview)
  - [Signal-Based Human Interaction](#signal-based-human-interaction)
  - [Document Validation Activity](#document-validation-activity)
  - [7-Day Timeout](#7-day-timeout)
  - [Workflow State & Queries](#workflow-state--queries)
- [API Endpoints](#api-endpoints)
- [Project Structure](#project-structure)

---

## Features

- ✅ **Durable Workflow**: Survives crashes and restarts without losing progress
- ✅ **Human-in-the-Loop**: Waits for user input via Temporal Signals
- ✅ **AI Validation**: Documents validated using Google Gemini AI
- ✅ **7-Day Timeout**: Auto-expires if documents aren't submitted in time
- ✅ **Real-time Status**: Query workflow state at any time
- ✅ **Beautiful UI**: Modern Vue.js + TailwindCSS interface

---

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Vue.js UI     │────▶│   FastAPI       │────▶│   Temporal      │
│   (index.html)  │     │   (main.py)     │     │   Server        │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                        │
                                                        ▼
                                               ┌─────────────────┐
                                               │   Temporal      │
                                               │   Worker        │
                                               └─────────────────┘
                                                        │
                                    ┌───────────────────┼───────────────────┐
                                    ▼                   ▼                   ▼
                            ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                            │  Workflow   │     │  Activity   │     │  Gemini AI  │
                            │  (signals)  │     │ (validate)  │     │  (LLM)      │
                            └─────────────┘     └─────────────┘     └─────────────┘
```

---

## Installation

### 1. Install Temporal CLI

Temporal CLI is required to run the local development server.

**macOS / Linux:**
```bash
curl -sSf https://temporal.download/cli.sh | sh
```

This installs the CLI to `~/.temporalio/bin/temporal`.

**Verify installation:**
```bash
~/.temporalio/bin/temporal --version
```

**Alternative (Homebrew on macOS):**
```bash
brew install temporal
```

### 2. Install Python Dependencies

Using the virtual environment:

```bash
~/.venv/bin/pip install -r requirements.txt
```

**Dependencies:**
- `fastapi` - Web framework
- `uvicorn` - ASGI server
- `temporalio` - Temporal Python SDK
- `google-genai` - Google Gemini AI SDK
- `pydantic` - Data validation
- `python-dotenv` - Environment variable management

### 3. Configure Environment Variables

Create a `.env` file in the project root:

```bash
touch .env
```

Add your Gemini API key:

```env
GOOGLE_API_KEY=your-gemini-api-key-here
```

**Get a Gemini API key:**
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click "Create API Key"
3. Copy the key and paste it in your `.env` file

---

## Running the Application

### Step 1: Start Temporal Server

```bash
~/.temporalio/bin/temporal server start-dev --db-filename /tmp/temporal.db
```

This starts:
- **Temporal Server** on `localhost:7233`
- **Temporal Web UI** on `http://localhost:8233`

### Step 2: Start the Application

In a new terminal:

```bash
cd /Users/josemiguel/request-documents-example
~/.venv/bin/python main.py
```

This starts:
- **FastAPI Server** on `http://localhost:8000`
- **Temporal Worker** (in a subprocess)

### Step 3: Open the Portal

Navigate to **http://localhost:8000** in your browser.

---

## How the Workflow Works

### Workflow Overview

The `DocumentRequestWorkflow` orchestrates the document verification process:

```
┌──────────────────────────────────────────────────────────────────┐
│                    DocumentRequestWorkflow                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                   │
│  1. Workflow starts → Status: "Waiting for documents"            │
│                           │                                       │
│                           ▼                                       │
│  2. WAIT for condition: all 3 documents valid                    │
│     └─ Timeout: 7 days                                           │
│                           │                                       │
│         ┌─────────────────┼─────────────────┐                    │
│         ▼                 ▼                 ▼                    │
│    [Signal 1]        [Signal 2]        [Signal 3]                │
│    Full Name         Passport          Address                   │
│         │                 │                 │                    │
│         ▼                 ▼                 ▼                    │
│    [Activity]        [Activity]        [Activity]                │
│    Validate          Validate          Validate                  │
│    via Gemini        via Gemini        via Gemini                │
│         │                 │                 │                    │
│         └─────────────────┼─────────────────┘                    │
│                           ▼                                       │
│  3. All valid? ─────────────────────────────────────────────────▶│
│     YES: Complete workflow with success                          │
│     NO:  Keep waiting for more signals                           │
│     TIMEOUT: Complete workflow with timeout status               │
│                                                                   │
└──────────────────────────────────────────────────────────────────┘
```

### Signal-Based Human Interaction

**What are Signals?**

Signals are Temporal's mechanism for sending data to a running workflow from external sources. They enable the "human-in-the-loop" pattern.

```python
@workflow.signal
async def process_submission(self, document_type: str, content: str) -> None:
    """Process a document submission by validating it."""
    # This runs inside the workflow when a signal is received
    result = await workflow.execute_activity(
        validate_document,
        args=[document_type, content],
        start_to_close_timeout=timedelta(seconds=60),
    )
    # Update internal state based on validation result
```

**How it works:**

1. User submits a document via the web form
2. FastAPI endpoint receives the submission
3. FastAPI sends a **Signal** to the running workflow:
   ```python
   await handle.signal(
       DocumentRequestWorkflow.process_submission,
       args=[document_type, content],
   )
   ```
4. The workflow receives the signal and executes the validation activity
5. Workflow state is updated with the validation result
6. If all 3 documents are valid, the `wait_condition` is satisfied

### Document Validation Activity

**What are Activities?**

Activities are the building blocks for performing actual work (API calls, database operations, etc.). They can be retried automatically if they fail.

```python
@activity.defn
async def validate_document(document_type: str, content: str) -> dict:
    """Validate a document using Gemini AI."""
    
    # 1. Create Gemini client
    client = genai.Client(api_key=api_key)
    
    # 2. Generate validation prompt based on document type
    prompt = get_validation_prompt(doc_type, content)
    
    # 3. Call Gemini AI
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt,
    )
    
    # 4. Parse and return result
    return {
        "document_type": document_type,
        "is_valid": result.get("is_valid", False),
        "message": result.get("message", "..."),
    }
```

**Validation Rules:**

| Document | Requirements |
|----------|-------------|
| **Full Name** | First + last name, alphabetic characters only |
| **Passport** | Passport number (6-9 alphanumeric) + nationality |
| **Address** | Street name + number, optionally city/state/zip |

### 7-Day Timeout

The workflow uses `wait_condition` with a timeout to implement the 7-day deadline:

```python
@workflow.run
async def run(self, request_id: str) -> dict:
    # Wait for all documents to be valid OR timeout after 7 days
    try:
        await workflow.wait_condition(
            lambda: self._document_status.all_valid(),
            timeout=timedelta(days=7),
        )
    except TimeoutError:
        # 7 days elapsed without all documents validated
        self._status = "Timed out - 7 days elapsed"
        return {"status": "timeout", ...}
    
    # All documents validated successfully!
    return {"status": "completed", ...}
```

**Key points:**
- The workflow **pauses** at `wait_condition` without consuming resources
- If the condition becomes true (all docs valid), execution continues
- If 7 days pass, a `TimeoutError` is raised
- The workflow is **durable**: it survives server restarts

### Workflow State & Queries

**Queries** allow external systems to read workflow state without modifying it:

```python
@workflow.query
def get_status(self) -> dict:
    """Query to get current workflow status."""
    return {
        "status": self._status,
        "documents": self._document_status.to_dict(),
        "all_valid": self._document_status.all_valid(),
        "completed": self._completed,
    }
```

**Usage from FastAPI:**
```python
status = await handle.query(DocumentRequestWorkflow.get_status)
```

The frontend polls this query every 5 seconds to update the UI in real-time.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/` | Serve the frontend HTML |
| `POST` | `/api/workflow/start` | Start a new document request workflow |
| `POST` | `/api/document/submit` | Submit a document for validation |
| `GET` | `/api/workflow/{id}/status` | Get workflow status |

**Example: Start Workflow**
```bash
curl -X POST http://localhost:8000/api/workflow/start \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Example: Submit Document**
```bash
curl -X POST http://localhost:8000/api/document/submit \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "doc-request-xxx",
    "document_type": "full_name",
    "content": "John Smith"
  }'
```

---

## Project Structure

```
request-documents-example/
├── .env                 # Environment variables (GOOGLE_API_KEY)
├── requirements.txt     # Python dependencies
├── models.py           # Data models (DocumentType, DocumentStatus)
├── activities.py       # Temporal activity (validate_document)
├── workflow.py         # Temporal workflow (DocumentRequestWorkflow)
├── main.py             # FastAPI app + Worker lifecycle
├── index.html          # Vue.js + TailwindCSS frontend
├── setup.md            # Quick setup guide
└── README.md           # This file
```

---

## Temporal Web UI

View and debug workflows at **http://localhost:8233**

You can:
- See all running/completed workflows
- Inspect workflow history (events)
- View signal and query calls
- Manually send signals to workflows

---

## License

MIT
