# SecureKnowledge

A production-grade, permission-aware knowledge assistant built for secure organizational document search and question answering.

SecureKnowledge combines multi-tenant access control, hybrid retrieval, cited answers, document ingestion, evaluations, audit logs, and production-oriented observability.

## Project goal

The main goal is to demonstrate how a reliable AI knowledge assistant should be designed when documents have different visibility rules.

A user must never retrieve, cite, summarize, or indirectly access information from a document they are not authorized to view.

Permission filtering happens during retrieval, before document chunks are passed to the language model.

## Planned capabilities

* Multi-tenant organizations and workspaces
* User, group, workspace, and document-level permissions
* PDF and text document ingestion
* Asynchronous document processing
* PostgreSQL full-text search
* Vector search with pgvector
* Hybrid retrieval and result fusion
* Answers with document and passage citations
* Answer abstention when evidence is insufficient
* Conversation history
* Retrieval traces
* Token, latency, and cost tracking
* Administrative review interface
* Audit logs
* Evaluation datasets and automated evaluation runs
* Authorization-leakage tests

## Architecture

SecureKnowledge is organized as a monorepo with three independently deployable applications.

```text
secure-knowledge/
├── apps/
│   ├── api/
│   ├── worker/
│   └── web/
├── packages/
│   └── secure-knowledge-core/
├── infrastructure/
├── tests/
├── docs/
├── docker-compose.yml
└── README.md
```

### API

The FastAPI application handles:

* authentication
* organizations and workspaces
* users, roles, and memberships
* document metadata
* permission management
* query orchestration
* conversations
* audit and administration endpoints

### Worker

The worker handles asynchronous jobs such as:

* document extraction
* text normalization
* chunking
* embedding generation
* indexing
* document reprocessing
* evaluation runs
* cleanup tasks

Cleanup periods, preserved aggregates, and organization-specific audit
requirements are documented in the [data retention policy](docs/retention-policy.md).

### Web

The React and TypeScript application provides:

* authentication
* workspace management
* document upload
* permission management
* knowledge-assistant interface
* citations
* conversation history
* retrieval review
* evaluation dashboards
* audit-log views

### Shared core package

The API and worker use a shared Python package containing:

* configuration and logging
* database models and repositories
* authorization policies
* ingestion pipelines
* retrieval logic
* model-provider integrations
* evaluation tooling

## Technology stack

### Backend

* Python
* FastAPI
* Pydantic
* SQLAlchemy
* Alembic
* PostgreSQL
* pgvector
* Redis

### AI and retrieval

* LLM APIs
* embeddings
* PostgreSQL full-text search
* vector similarity search
* hybrid retrieval
* reciprocal-rank fusion
* optional reranking
* structured model outputs
* retrieval and answer evaluations

### Frontend

* React
* TypeScript
* Vite
* TanStack Query
* React Router

### Infrastructure

* Docker
* Docker Compose
* AWS
* S3
* RDS
* ECS Fargate
* ElastiCache
* CloudWatch
* GitHub Actions

## Security model

Authorization is enforced before retrieval results reach the language model.

Incorrect approach:

```text
Retrieve relevant documents
        ↓
Ask the model not to reveal restricted information
```

SecureKnowledge approach:

```text
Authenticate user
        ↓
Resolve organization and workspace permissions
        ↓
Determine authorized documents
        ↓
Retrieve only authorized chunks
        ↓
Generate a cited answer
```

The model never receives unauthorized document content.

## Permission levels

The planned authorization model includes:

* organization membership
* organization roles
* workspace membership
* workspace roles
* group membership
* organization-wide documents
* workspace-visible documents
* group-restricted documents
* user-restricted documents
* owner-only documents

## Current status

The project is currently in the foundation stage.

Implemented or in progress:

* monorepo structure
* API, worker, and web applications
* shared Python package
* Docker Compose environment
* PostgreSQL setup
* SQLAlchemy models
* Alembic migrations
* users
* organizations
* organization memberships
* workspaces
* workspace memberships
* authentication
* JWT access tokens
* initial tenancy rules

## Development roadmap

### Milestone 1 — Foundation and tenancy

* authentication
* organizations
* workspaces
* memberships
* tenant isolation
* authorization tests

### Milestone 2 — Document permissions

* groups
* document visibility
* user-level document permissions
* centralized authorization service
* access-control integration tests

### Milestone 3 — Document ingestion

* uploads
* object storage
* PDF and text extraction
* document versioning
* chunking
* embeddings
* asynchronous processing

### Milestone 4 — Retrieval

* vector retrieval
* full-text retrieval
* hybrid retrieval
* permission-aware filtering
* result fusion
* retrieval traces

### Milestone 5 — Answer generation

* structured outputs
* citations
* abstention
* conversations
* streaming responses
* token and cost tracking

### Milestone 6 — Evaluation

* evaluation datasets
* retrieval recall
* citation correctness
* groundedness
* answer relevance
* abstention quality
* unauthorized retrieval rate

### Milestone 7 — Administration and deployment

* retrieval review interface
* audit-log interface
* usage dashboard
* AWS deployment
* CI/CD
* threat model
* architecture documentation

## Local development

### Requirements

* Python 3.12+
* uv
* Node.js
* Docker
* Docker Compose

### Setup

Clone the repository:

```bash
git clone https://github.com/richardj46/secure-knowledge
cd secure-knowledge
```

Create the environment file:

```bash
cp .env.example .env
```

Install Python dependencies:

```bash
uv sync
```

Start PostgreSQL, Redis, API, worker, and web applications:

```bash
docker compose up --build
```

API health endpoint:

```text
http://localhost:8000/health
```

Frontend:

```text
http://localhost:5173
```

API documentation:

```text
http://localhost:8000/docs
```

## Development commands

Run the ingestion worker locally:

```bash
uv run celery \
  -A secure_knowledge_worker.celery_app:celery_app \
  worker \
  --loglevel=INFO
```

Run tests:

```bash
uv run pytest
```

Run lint checks:

```bash
uv run ruff check .
```

Run formatting checks:

```bash
uv run ruff format --check .
```

Run type checking:

```bash
uv run mypy .
```

Apply database migrations:

```bash
uv run alembic \
  -c infrastructure/database/alembic.ini \
  upgrade head
```

Create a migration:

```bash
uv run alembic \
  -c infrastructure/database/alembic.ini \
  revision \
  --autogenerate \
  -m "describe migration"
```

## Portfolio focus

This project is designed to demonstrate production AI application engineering skills, including:

* secure multi-tenant architecture
* authentication and authorization
* relational data modelling
* asynchronous processing
* retrieval-augmented generation
* hybrid search
* AI evaluation
* auditability
* observability
* cost and latency controls
* cloud deployment
* human review workflows

## Non-goals for the initial version

The initial version will not include:

* unrestricted autonomous agents
* internet browsing
* OCR-heavy scanned documents
* fine-tuning
* Slack or Teams synchronization
* Google Drive synchronization
* complex billing
* many model providers
* large-scale distributed vector infrastructure

## License

This project is licensed under the MIT License.
