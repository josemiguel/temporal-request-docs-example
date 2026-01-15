# Document Verification Portal

A Temporal workflow-based document verification system with FastAPI backend and Vue.js frontend.

## Features

- **Temporal Workflow**: Document request workflow with 7-day timeout and human signal handling
- **AI Validation**: Documents validated using Google Gemini AI
- **Beautiful UI**: Vue.js + TailwindCSS responsive interface
- **Real-time Status**: Live workflow status updates

## Required Documents

1. **Full Name** - First and last name of a person
2. **Passport** - Passport number with nationality
3. **Address** - Residential address

## Setup

### 1. Install Dependencies

```bash
~/.venv/bin/pip install -r requirements.txt
```

### 2. Set Gemini API Key

Edit the `.env` file and add your API key:

```
GOOGLE_API_KEY=your-gemini-api-key
```

### 3. Start Temporal Server

```bash
~/.temporalio/bin/temporal server start-dev --db-filename /tmp/temporal.db
```

### 4. Start the Application

```bash
~/.venv/bin/python main.py
```

### 5. Open the Portal

Navigate to http://localhost:8000

## Architecture

- `models.py` - Data models for documents and validation
- `activities.py` - Temporal activity for Gemini validation
- `workflow.py` - Temporal workflow with signals and 7-day timeout
- `main.py` - FastAPI server with worker in lifespan
- `index.html` - Vue.js + TailwindCSS frontend

## Temporal UI

View workflow status at http://localhost:8233