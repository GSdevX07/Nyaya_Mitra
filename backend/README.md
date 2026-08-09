# Nyaya Mitra - Backend

The backend of Nyaya Mitra is built with FastAPI and runs an agentic AI system for legal operations. It uses a fault-tolerant 3-tier architecture to evaluate undertrial prisoner records for bail eligibility under BNSS 479, check document completeness, prioritize cases, and generate bail application drafts.

## System Architecture

1.  **Primary Cloud Tier:** Groq API (`llama-3.1-8b-instant`) for blazing-fast inference.
2.  **Enterprise Cloud Tier:** IBM Watsonx.ai (`granite-3-8b-instruct`) for enterprise-grade deterministic LLM fallback.
3.  **Local Edge LLM Tier:** Ollama (`granite4.1:8b`) for when cloud services fail or timeout.
4.  **Deterministic Pre-computed Safety Fallback:** Hardcoded mock responses ensuring the demo never crashes, even without internet.

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv) or `pip`
- [Ollama](https://ollama.com/) (Optional, for local edge LLM tier)

### 2. Environment Variables
1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
2. Open `.env` and configure your API keys:
   - `GROQ_API_KEY`: Required for Tier 1 inference. Get one at [console.groq.com](https://console.groq.com/keys).
   - `SUPABASE_URL` and `SUPABASE_SERVICE_KEY`: Required for persistent state management.
   - `WATSONX_API_KEY` and `WATSONX_PROJECT_ID`: (Optional) For Tier 1.5 enterprise-grade inference.

### 3. Local Model Setup (Optional)
If you want to test the Tier 2 local edge fallback, install Ollama and pull the Granite model:
```bash
ollama run granite4.1:8b
```
Keep the Ollama app running in the background.

### 4. Installation
Install the project dependencies:
```bash
pip install -r requirements.txt
```

### 5. Running the Backend Server
Start the FastAPI server with hot-reloading:
```bash
uvicorn app.main:app --reload --port 8000
```
The server will be available at `http://localhost:8000`.

### 6. Interactive API Docs
Swagger UI documentation is automatically generated. Visit:
[http://localhost:8000/docs](http://localhost:8000/docs)

## Key Endpoints
- `GET /cases` - Retrieves all cases sorted by urgency score.
- `GET /cases/available` - Retrieves available undertrial cases that can be assigned.
- `GET /cases/{case_id}` - Runs the full 8-agent pipeline on a single case.
- `POST /cases/assess-document` - Runs the multi-stage document AI pipeline.

## Automated Testing
You can smoke-test individual agents by running them as scripts. For example:
```bash
python -m app.agents.orchestrator
python -m app.agents.eligibility_agent
python -m app.agents.retrieval_agent
```
