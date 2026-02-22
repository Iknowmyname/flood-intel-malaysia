# HydroIntel MY: Malaysia Flood Intelligence Assistant

HydroIntel MY is a full-stack flood intelligence system that combines:
- Deterministic hydro analytics (rainfall + river level summaries and heuristic flood risk),
- Retrieval-augmented generation (RAG) over a local vector database,
- Guided chat UI for non-technical users.

It is built as a multi-service architecture:
- `infobanjir-frontend` (Angular + Nginx)
- `infobanjir-api` (Java 17 + Spring Boot orchestration API)
- `infobanjir-rag` (Python FastAPI + ChromaDB vector retrieval + LLM-Based Responses)

## Live Demo

- Demo URL: `http://ec2-54-169-123-68.ap-southeast-1.compute.amazonaws.com/`
- Public demo note:
  - This deployment is an early preview and still under active iteration.
  - The public environment runs in limited mode with conservative defaults due to deployment cost constraints.
  - LLM generation is disabled in the live demo (`RAG_USE_LLM=false`), so responses are retrieval/deterministic-first rather than fully generative.
  - Outputs are operational guidance and heuristic summaries, not official flood warnings.

## Why This Project

- Converts live flood observations from the flood monitoring system which I have built into readable operational insights.
- Supports both direct metric queries and context-style questions.
- Demonstrates end-to-end engineering of frontend, backend orchestration, RAG, ingestion, and cloud deployment.


## Architecture

```mermaid
%%{init: {
  "theme": "base",
  "themeVariables": {
    "primaryColor": "#0f172a",
    "primaryTextColor": "#e2e8f0",
    "primaryBorderColor": "#334155",
    "lineColor": "#64748b",
    "secondaryColor": "#111827",
    "tertiaryColor": "#1f2937",
    "fontFamily": "Inter, Segoe UI, Arial"
  }
}}%%

flowchart TB

    U([User]):::actor

    subgraph CLIENT[Client Layer]
        F[Angular Frontend]:::frontend
    end

    subgraph APP[Application Layer]
        A[Spring Boot Backend<br/>Orchestrator]:::api
        R[FastAPI RAG Service<br/>Knowledge-Based Answers]:::rag
    end

    subgraph DATA[Data Layer]
        E[(Flood Database PostgreSQL via REST API)]:::upstream
        C[(ChromaDB Vector Store)]:::vector
        O[(Ollama LLM - Optional)]:::llm
    end

    U --> F
    F -->|User Question| A

    %% Deterministic Flow
    A -->|Fetch Live Metrics| E
    E -->|Flood Data| A

    %% RAG Flow
    A -->|Request Knowledge Answer| R
    R -->|Retrieve Context| C
    R -->|Generate Response| O
    R -->|RAG Answer| A

    %% Unified Response
    A -->|Final Response| F

    style CLIENT fill:transparent,stroke:transparent,color:#cbd5e1
    style APP fill:transparent,stroke:transparent,color:#cbd5e1
    style DATA fill:transparent,stroke:transparent,color:#cbd5e1

    classDef actor fill:#020617,color:#f8fafc,stroke:#334155,stroke-width:1.6px;
    classDef frontend fill:#0b1324,color:#e2e8f0,stroke:#38bdf8,stroke-width:1.6px;
    classDef api fill:#111827,color:#f1f5f9,stroke:#60a5fa,stroke-width:1.6px;
    classDef rag fill:#172554,color:#e0e7ff,stroke:#818cf8,stroke-width:1.6px;
    classDef upstream fill:#1f2937,color:#e5e7eb,stroke:#94a3b8,stroke-width:1.6px;
    classDef vector fill:#0f172a,color:#dbeafe,stroke:#22d3ee,stroke-width:1.6px;
    classDef llm fill:#111827,color:#ede9fe,stroke:#a78bfa,stroke-width:1.6px;
```

## RAG Query Pipeline

```mermaid
flowchart LR

    Q[User Question] --> S[State & Constraint Inference]
    S --> R[Semantic + Keyword Retrieval]
    R --> C[(ChromaDB)]

    R -->|Context Found| G[Response Generation]
    R -->|No Context| N[No Matching Sources]

    G -->|LLM Enabled| O[(Ollama)]
    G -->|LLM Disabled| D[Deterministic Summary]

    O --> A[Final Answer]
    D --> A
```

## Ingestion Pipeline for RAG Document Generation

```mermaid
flowchart LR

    U[(Flood Data API)] --> F[Periodic Fetch]
    F --> T[Document Builder]

    T --> R[Rainfall Docs]
    T --> W[Water-Level Docs]
    T --> H[Flood-Risk Docs]

    R --> C[(ChromaDB)]
    W --> C
    H --> C
```

## Core Capabilities

- Flood risk estimation from latest rainfall + river-level signals.
- State-aware rainfall and river-level summaries.
- Hybrid answer strategy:
  - Deterministic path for operational flood related queries,
  - RAG path for knowledge and context queries.
- Auto-ingestion from upstream API into ChromaDB with periodic refresh.
- Graceful fallback behavior when dependent services are unavailable.

## Tech Stack

- Frontend: Angular 17, TypeScript, Nginx
- API: Java 17, Spring Boot, Spring MVC, RestTemplate, Maven, JUnit 5
- RAG: Python 3.11, FastAPI, ChromaDB, sentence-transformers, uvicorn
- Deployment: Docker, Docker Compose, AWS EC2
- Data Source: upstream REST API backed by PostgreSQL

## Repository Structure

```text
.
|- infobanjir-frontend/   # Angular app + Nginx runtime proxy/env injection
|- infobanjir-api/        # Spring Boot orchestration API
|- infobanjir-rag/        # FastAPI RAG service + ingestion + vector store logic
|- docker-compose.yml     # Multi-service local/prod-style orchestration
`- aws.env.template       # Environment variable template
```

## Quick Start (Docker Compose)

### 1) Prepare env file

```bash
cp aws.env.template aws.env
```

Adjust values as needed in `aws.env`:
- `APP_MODE=auto`
- `RAG_USE_LLM=false` (recommended for lightweight deployment)
- `CHROMA_HOST_PATH=./.data/chroma` (or an EBS-backed path in EC2)

### 2) Build and run

```bash
docker compose --env-file aws.env up -d --build
```

### 3) Verify services

```bash
docker compose --env-file aws.env ps
curl http://localhost/api/health
curl http://localhost/rag/health
curl http://localhost/rag/stats
```

Frontend should be available at:
- `http://localhost` (or the host/port you mapped via `FRONTEND_PORT`)

## Local Development (Without Docker)

### Frontend

```bash
cd infobanjir-frontend
npm install
npm start
```

### API

```bash
cd infobanjir-api
./mvnw spring-boot:run
```

Windows:

```powershell
cd infobanjir-api
.\mvnw.cmd spring-boot:run
```

### RAG

```bash
cd infobanjir-rag
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows:

```powershell
cd infobanjir-rag
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API Usage

### Ask endpoint (main entrypoint)

`POST /api/ask`

Request:

```json
{
  "question": "What is the flood risk in Selangor today?"
}
```

Response shape:

```json
{
  "status": "success",
  "data": {
    "answer": "Estimated flood risk in SEL is Moderate ...",
    "mode": "auto",
    "confidence": 0.85,
    "latencyMs": 320,
    "requestId": "....",
    "timestamp": "...."
  },
  "timeStamp": "....",
  "requestId": "...."
}
```

### Useful health/debug endpoints

- `GET /api/health`
- `GET /rag/health`
- `GET /rag/health/llm`
- `GET /rag/stats`
- `GET /rag/stats/by-state`
- `GET /rag/ingest/status`

## RAG and Vector Store Notes

- ChromaDB persists to `CHROMA_PERSIST_DIR` inside container and maps to `CHROMA_HOST_PATH` on host.
- Auto-ingestion runs on startup and refreshes every `AUTO_INGEST_REFRESH_SECONDS`.
- Default ingestion behavior replaces existing collection content per refresh (`replace=True`) to keep local KB aligned with latest upstream snapshots.
- Retrieval combines semantic similarity + keyword matching with configurable:
  - `RAG_TOP_K`
  - `RAG_MIN_SCORE`

## LLM Mode

- Local LLM via Ollama:
  - set `RAG_USE_LLM=true`
  - configure `OLLAMA_BASE_URL` and `OLLAMA_MODEL` (default `mistral`)
- If LLM is disabled/unavailable, the system falls back to deterministic summary generation from retrieved context.

## Deployment Notes (AWS EC2)

- Deploy with Docker Compose on EC2.
- Persist ChromaDB on a durable host path (prefer EBS-backed directory).
- Expose only frontend publicly; keep internal service communication container-to-container.
- If using CloudFront in front of EC2, ensure `/api/*` and `/rag/*` routes are forwarded correctly with non-cached dynamic behavior.

## Testing

API:

```bash
cd infobanjir-api
./mvnw test
```

RAG:

```bash
cd infobanjir-rag
pytest
```
