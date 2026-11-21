# IntelliChat OCR – Agentic AI Healthcare Document Processing

An AI-powered healthcare document intelligence and insurance claim processing system built using **Python, FastAPI, Azure AI Content Understanding, Azure OpenAI, and LangGraph**.

IntelliChat OCR automates healthcare document classification, information extraction, claim validation, discrepancy analysis, and human-in-the-loop claim review.

---

## 1. Project Overview

Healthcare insurance claims involve multiple documents, including hospital bills, insurance claim forms, discharge summaries, and laboratory reports.

Manually reviewing these documents is time-consuming and can lead to errors.

IntelliChat OCR addresses this problem through an intelligent document processing pipeline that:

- Uploads healthcare documents to Azure Blob Storage.
- Classifies documents using Azure AI Content Understanding.
- Extracts structured information from PDF documents.
- Stores raw and normalized extraction results in PostgreSQL.
- Aggregates documents under a single insurance claim.
- Validates patient information across documents.
- Uses Azure OpenAI GPT-5.1 to analyze discrepancies.
- Uses LangGraph to orchestrate AI agents.
- Supports human-in-the-loop review with workflow pause and resume.

## 2. Key Features

### Intelligent Document Processing
- PDF document upload.
- Azure Blob Storage integration.
- Document classification.
- OCR and structured field extraction.
- Confidence scores and field metadata.
- Raw and structured extraction storage.

### Supported Document Types

1. Hospital Bill
2. Insurance Claim Form
3. Discharge Summary
4. Laboratory Report

### Claim Management
- Create insurance claims.
- Upload multiple documents against a claim.
- Aggregate extracted document information.
- Track claim processing status.
- Retrieve claim details and document information.

### AI-Based Validation
- Patient name consistency validation.
- Patient ID consistency validation.
- Cross-document discrepancy detection.
- Validation results with severity and extracted values.

### Agentic AI Workflow

Three specialized agents coordinate claim processing:

| Agent | Responsibility |
|---|---|
| Claim Validation Agent | Executes deterministic validation rules |
| Claim Analysis Agent | Uses Azure OpenAI GPT-5.1 to analyze discrepancies |
| Claim Decision Agent | Determines the next workflow action |

### Human-in-the-Loop
- Pause workflows requiring manual review.
- Persist workflow checkpoints in PostgreSQL.
- Accept reviewer decisions.
- Resume paused workflows using LangGraph.
- Maintain claim review history.

---

## 3. System Architecture

```text
                 CLIENT / SWAGGER
                        |
                        v
                  FASTAPI BACKEND
                        |
             DOCUMENT UPLOAD API
                        |
                        v
                AZURE BLOB STORAGE
                        |
                        v
          AZURE AI CONTENT UNDERSTANDING
                        |
              DOCUMENT CLASSIFICATION
                        |
                 FIELD EXTRACTION
                        |
                        v
              EXTRACTION NORMALIZATION
                        |
                        v
                  POSTGRESQL
                        |
                        v
                CLAIM AGGREGATION
                        |
                        v
              LANGGRAPH ORCHESTRATOR
                        |
              +---------+---------+
              |                   |
              v                   v
       VALIDATION AGENT      INCOMPLETE CLAIM
              |
              v
        ANALYSIS AGENT
              |
              v
       AZURE OPENAI GPT-5.1
              |
              v
        DECISION AGENT
              |
       +------+------+
       |             |
       v             v
   VALIDATED      NEEDS REVIEW
                     |
                     v
              HUMAN REVIEW
                     |
                     v
              LANGGRAPH RESUME
                     |
                     v
                POSTGRESQL
```

---

## 4. Technology Stack

| Category | Technologies |
|---|---|
| Backend | Python, FastAPI |
| AI / LLM | Azure OpenAI GPT-5.1 |
| Document Intelligence | Azure AI Content Understanding |
| Agent Framework | LangGraph |
| LLM Integration | LangChain |
| Database | PostgreSQL |
| ORM | SQLAlchemy |
| Migrations | Alembic |
| Cloud Storage | Azure Blob Storage |
| Workflow Persistence | LangGraph PostgreSQL Checkpointer |
| API Documentation | Swagger / OpenAPI |
| Logging | Python Logging |

---

## 5. Project Structure

```text
IntelliChat-OCR/
│
├── app/
│   ├── agents/
│   │   ├── base_agent.py
│   │   ├── validation_agent.py
│   │   ├── caim_analysis_agent.py
│   │   └── decision_agent.py
│   │
│   ├── api/
│   │   ├── document_router.py
│   │   └── claim_router.py
│   │
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── logging.py
│   │
│   ├── models/
│   │   ├── document.py
│   │   ├── claim.py
│   │   └── claim_review.py
│   │
│   ├── services/
│   │   ├── blob_storage.py
│   │   ├── document_classifier.py
│   │   ├── document_extractor.py
│   │   ├── claim_aggregation.py
│   │   ├── azure_openai.py
│   │   └── validation/
│   │       ├── claim_validation.py
│   │       └── validation_rules.py
│   │
│   ├── workflows/
│   │   ├── claim_state.py
│   │   └── claim_workflow.py
│   │
│   └── main.py
│
├── alembic/
├── tests/
├── .env.example
├── .gitignore
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## 6. Database Design

The application uses PostgreSQL with SQLAlchemy.

### Claims

Stores insurance claim information.

Important fields:
- id
- claim_number
- insured_person_name
- policy_number
- patient_name
- hospital_name
- status
- validation_result
- created_at
- updated_at

### Documents

Stores uploaded document information and extraction results.

Important fields:
- id
- filename
- blob_name
- claim_id
- document_type
- status
- analysis_result
- structured_result
- error_message
- created_at
- updated_at

### Claim Reviews

Stores reviewer actions and review history.

Important fields:
- id
- claim_id
- action
- reviewer
- comments
- created_at

### LangGraph Checkpoints

LangGraph maintains its workflow state and checkpoint history in PostgreSQL using its PostgreSQL checkpointer.

---

## 7. API Endpoints

### Claim Management

| Method | Endpoint | Description |
|---|---|---|
| POST | `/claims` | Create a claim |
| POST | `/claims/{claim_id}/documents` | Upload claim documents |
| POST | `/claims/process/{document_id}` | Process an uploaded document |
| GET | `/claims/{claim_id}/aggregate` | Aggregate claim documents |

### Claim Validation

| Method | Endpoint | Description |
|---|---|---|
| GET | `/claims/{claim_id}/validate` | Execute claim validation |
| GET | `/claims/{claim_id}/validation-result` | Retrieve validation results |

### Claim Review

| Method | Endpoint | Description |
|---|---|---|
| GET | `/claims/review-queue` | Retrieve claims requiring review |
| GET | `/claims/{claim_id}/review-details` | Retrieve detailed claim information |
| POST | `/claims/{claim_id}/review` | Submit a reviewer action |
| GET | `/claims/{claim_id}/reviews` | Retrieve review history |

### Agentic AI Workflow

| Method | Endpoint | Description |
|---|---|---|
| POST | `/claims/{claim_id}/run-workflow` | Execute LangGraph claim workflow |
| POST | `/claims/{claim_id}/resume-workflow` | Resume a paused workflow after human review |

---

## 8. Agentic AI Workflow

The application uses LangGraph to coordinate specialized agents.

### Workflow Execution

**Step 1 – Claim Validation Agent**

Executes deterministic validation rules to identify inconsistencies across submitted documents.

Current validation rules:
- Patient name consistency.
- Patient ID consistency.

**Step 2 – Claim Analysis Agent**

Uses Azure OpenAI GPT-5.1 to:
- Analyze validation findings.
- Identify document discrepancies.
- Explain potential issues.
- Recommend the next action.

**Step 3 – Claim Decision Agent**

Determines the next workflow action based on validation status.

Possible outcomes:
- Validated.
- Needs review.
- Incomplete.

**Step 4 – Human-in-the-Loop**

When a claim requires manual review:
- LangGraph pauses execution using `interrupt()`.
- Workflow state is persisted using PostgreSQL.
- A reviewer submits a decision.
- The workflow resumes using `Command(resume=...)`.

Supported reviewer actions:
- Approved.
- Rejected.
- Requires information.

---

## 9. Local Development Setup

### Prerequisites

- Python 3.11+
- PostgreSQL
- Azure subscription
- Azure Blob Storage account
- Azure AI Content Understanding resource
- Azure OpenAI deployment

### Step 1 – Clone Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd IntelliChat-OCR
```

### Step 2 – Create Virtual Environment

```bash
python -m venv ocrenv
```

Activate on Windows:

```bash
ocrenv\Scripts\activate
```

### Step 3 – Install Dependencies

```bash
pip install -r requirements.txt
```

Ensure the project includes the LangGraph PostgreSQL checkpointer dependencies:

```bash
pip install langgraph-checkpoint-postgres "psycopg[binary,pool]"
```

### Step 4 – Configure Environment Variables

Create a `.env` file in the project root.

Configure the following values using your actual Azure and PostgreSQL credentials:

```env
DATABASE_URL=postgresql+psycopg://username:password@localhost:5432/smarthealth

AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/openai/v1
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_CHAT_DEPLOYMENT=gpt-5.1
```

Also configure the Azure Blob Storage and Azure Content Understanding credentials and analyzer settings required by your application.

Never commit `.env` or real credentials to Git.

### Step 5 – Run Database Migrations

```bash
alembic upgrade head
```

### Step 6 – Start FastAPI

```bash
uvicorn app.main:app --reload
```

Application:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

Health endpoint:

```text
http://127.0.0.1:8000/health
```

---

## 10. Logging and Monitoring

The application uses Python's logging module to monitor important operations.

Example events:
- Application startup and shutdown.
- Database connectivity.
- Azure OpenAI connectivity.
- Document upload.
- OCR processing.
- Claim aggregation.
- Agent execution.
- Workflow decisions.
- Human review and workflow resumption.

Sensitive information such as API keys, SAS tokens, passwords, and patient records should never be written to application logs.

---

## 11. Current Implementation Status

| Feature | Status |
|---|---|
| FastAPI backend | Implemented |
| Azure Blob Storage integration | Implemented |
| Four document analyzers | Implemented |
| Raw OCR response storage | Implemented |
| Structured extraction storage | Implemented |
| Claim aggregation | Implemented |
| Patient name validation | Implemented |
| Patient ID validation | Implemented |
| Azure OpenAI GPT-5.1 integration | Implemented |
| Validation Agent | Implemented |
| Analysis Agent | Implemented |
| Decision Agent | Implemented |
| LangGraph orchestration | Implemented |
| PostgreSQL checkpointer | Implemented |
| Human-in-the-loop pause/resume | Implemented |
| Claim review history | Implemented |
| Document resubmission | Planned |
| Production deployment | Planned |

---

## 12. Future Enhancements

- Document resubmission and version tracking.
- Additional healthcare-specific validation rules.
- React-based reviewer dashboard.
- Authentication and role-based access control.
- Production deployment on Azure.
- CI/CD automation using GitHub Actions.
- Application monitoring and distributed tracing.

---

## 13. Project Objective

IntelliChat OCR demonstrates how Generative AI, intelligent document processing, and Agentic AI can automate healthcare insurance claim workflows.

The system combines deterministic validation, LLM-based discrepancy analysis, multi-agent orchestration, and human oversight to build a reliable document intelligence solution.

**Built with Python, FastAPI, Azure AI, Azure OpenAI, PostgreSQL, and LangGraph.**
