# AI Knowledge Agent

An enterprise-grade agentic RAG (Retrieval-Augmented Generation) system powered by LangGraph, ChromaDB, and Anthropic's Claude.

## What It Does

Unlike simple RAG implementations that blindly retrieve and respond, this agent **reasons** about your questions:

1. **Analyzes** your question and optimizes the search query
2. **Searches** a vector knowledge base using semantic similarity
3. **Evaluates** whether the results are sufficient to answer
4. **Refines** its search strategy if needed (up to 2 iterations)
5. **Generates** a cited answer grounded in your documents

The agent maintains **conversation memory**, enabling natural multi-turn interactions with follow-up questions.

## Production Thinking

This project is a working prototype demonstrating the core patterns of an
enterprise agentic RAG system. It is **not production-ready as-is** — see
[PRODUCTION.md](PRODUCTION.md) for an honest inventory of what would need
to be added to deploy this at scale.

The project includes:

- **Containerized deployment** via Docker and docker-compose, mirroring a
  production service architecture with ChromaDB as a separate service
- **Evaluation framework** in `evals/` with regression tests covering
  retrieval quality, hallucination resistance, security, and latency — see
  [evals/README.md](evals/README.md)
- **Honest gap analysis** documenting the distance between prototype and
  production across observability, cost management, security, multi-tenancy,
  and infrastructure as code — see [PRODUCTION.md](PRODUCTION.md)

## Screenshot

![AI Knowledge Agent UI](images/ui-screenshot.png)

## Architecture
```
User Question
      │
      ▼
┌─────────────┐
│   Analyze    │ ← Optimizes query using conversation history
│   Question   │
└──────┬──────┘
       ▼
┌─────────────┐
│   Search     │ ← Semantic search via ChromaDB
│   Knowledge  │
│   Base       │
└──────┬──────┘
       ▼
┌─────────────┐     ┌──────────┐
│  Evaluate    │────▶│  Refine  │ ← Try different search angle
│  Results     │ No  │  Search  │
└──────┬──────┘     └─────┬────┘
       │ Yes              │
       ▼                  │
┌─────────────┐           │
│  Generate    │◀──────────┘
│  Answer      │
└─────────────┘
```

## Tech Stack

- **LangGraph** — Agentic workflow orchestration with state management
- **ChromaDB** — Local vector database with built-in embeddings
- **Anthropic Claude** — LLM for reasoning and answer generation
- **LangChain** — Foundation framework for LLM application building

## Quick Start
## Running with Docker (Recommended for Production-Like Testing)

The project ships with a Dockerfile and docker-compose stack that runs the
full application the way it would be deployed in production — with ChromaDB
as a separate service communicating over HTTP. This mirrors the enterprise
deployment pattern and eliminates "works on my machine" surprises.

### Prerequisites

- Docker Engine (or Docker Desktop)
- Docker Compose v2 (ships with modern Docker)

### Quick Start

```bash
# Clone the repo and create your .env file with API keys
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY (and optional OPENAI_API_KEY, MICROSOFT_CLIENT_ID)

# Build and start the full stack
docker compose up -d

# Open the app
open http://localhost:8501

# View logs
docker compose logs -f

# Stop the stack
docker compose down
```

### Architecture

The stack runs two containers connected by an internal Docker network:

- **agent** — the Streamlit application with the LangGraph agent
- **chroma** — ChromaDB vector store running in HTTP server mode

The agent detects its deployment mode automatically via the `CHROMA_HOST`
environment variable. Without it, the agent uses local persistent storage
(development mode). With it set, the agent connects to the ChromaDB service
over HTTP (containerized/Kubernetes mode). Same code, different deployment
shapes — this is the 12-factor configuration pattern.

### Dockerfile Design Notes

The Dockerfile uses a multi-stage build to keep the final image lean:

- **Builder stage** installs build tools and compiles Python dependencies
  into a virtual environment
- **Runtime stage** copies only the virtual environment and application
  code, runs as a non-root user, and includes a health check

This separation removes ~500MB of build toolchain from the final image
and follows container security best practices.

### Production Deployment

This docker-compose setup is a local development and testing target. For
production deployment at scale, see [PRODUCTION.md](PRODUCTION.md) for the
full production readiness inventory covering observability, cost management,
security, multi-tenancy, and infrastructure as code.

### Prerequisites

- Python 3.10+
- Anthropic API key ([get one here](https://console.anthropic.com))

### Installation
```bash
git clone https://github.com/mhourani/ai-knowledge-agent.git
cd ai-knowledge-agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration
```bash
cp .env.example .env
# Edit .env and add your Anthropic API key
```

### Usage

**1. Add documents to the `docs/` folder** (supports .txt, .pdf, .md)

**2. Ingest documents into the knowledge base:**
```bash
python3 main.py ingest
```

**3. Start asking questions:**
```bash
python3 main.py ask
```

**4. Reset the knowledge base:**
```bash
python3 main.py reset
```

### Example Session
```
You: What are the key dimensions of AI readiness?
Agent: Based on the knowledge base, there are five key dimensions...

You: Tell me more about the first one
Agent: Data maturity, the first dimension, refers to...

You: How does that relate to building POCs?
Agent: The connection between data maturity and POC success is...
```

## Project Structure
```
ai-knowledge-agent/
├── main.py               # CLI entry point
├── src/
│   ├── agent.py          # LangGraph agent with reasoning loop
│   ├── vectorstore.py    # ChromaDB vector store management
│   ├── loader.py         # Document loading and chunking
│   └── config.py         # Configuration settings
├── tests/
├── docs/                 # Place your documents here
├── requirements.txt
└── .env.example
```

## Roadmap

- [ ] Conversation memory ✅
- [ ] Word, PowerPoint, and Excel document support
- [ ] Image/multimodal document support
- [ ] OneDrive integration via Microsoft Graph API
- [ ] Streamlit web UI
- [ ] Comprehensive test suite with CI/CD
- [ ] Docker containerization

## Author

**Mark Hourani** — Enterprise AI Solution Architect
- Patent holder: U.S. Patent #9119056 (AI-driven knowledge management)
- [hourani.ai](https://hourani.ai)
- [LinkedIn](https://www.linkedin.com/in/markhourani)

## License

MIT
```