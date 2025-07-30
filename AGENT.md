# Agent Configuration for Search Comparisons Tool

Do not run any indefinite processes unless they are moved to the background
If there is an environment in the directory you want to run code in make sure the environment is active
For example before running any tests go to the root directory search-comparisons and do: source venv/bin/activate to activate the virtual environment for this project
## Commands
- **Test all**: `pytest backend/tests/`
- **Test single**: `pytest backend/tests/test_filename.py::test_function`
- **Test with coverage**: `pytest backend/tests/ --cov=backend/app --cov-report=html`
- **Lint**: `ruff check backend/` or `black backend/`
- **Format**: `black backend/`
- **Type check**: `mypy backend/`
- **Start local**: `./startup_with_logs.sh` (starts backend on :8001, frontend on :3001)
- **Stop servers**: `./stop_servers.sh` (stops both backend and frontend)
- **Backend only**: `cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001`

## Ports
- **Backend**: Always runs on port 8001 (http://localhost:8001)
- **Frontend**: Always runs on port 3001 (http://localhost:3001)
- **API endpoints**: Backend API available at http://localhost:8001/api/

## Architecture
- **FastAPI backend** in `backend/app/` with services, routes, API models, core config
- **Multi-engine search**: ADS, Google Scholar, Semantic Scholar, Web of Science
- **LLM integration**: Query intent service with Ollama/HuggingFace/OpenAI support
- **Key services**: `search_service.py` (main coordinator), `query_intent/service.py` (LLM query transformation), individual engine services
- **Caching**: LRU cache with TTL in `cache_service.py`
- **Local development**: Backend + frontend without Docker

## Code Style
- **Line length**: 88 chars (Ruff/Black config)
- **Imports**: Standard, third-party, local (`from app.services.ads_service import`)
- **Types**: Use `TypedDict` for structured data, `Optional[Type]` for nullable
- **Async**: Prefer `async def` for I/O operations, use `aiohttp` for HTTP
- **Logging**: Use module-level `logger = logging.getLogger(__name__)`
- **Error handling**: Use structured exceptions, log errors before raising
- **Naming**: snake_case for functions/vars, PascalCase for classes, descriptive names

## Security Configuration
- **Debug endpoints**: Secured with IP whitelist and optional API key authentication
- **CORS**: Explicit origin list, credentials disabled, explicit methods/headers only
- **TrustedHost**: Concrete domain list, no wildcards
- **Security headers**: CSP, X-Frame-Options, X-Content-Type-Options, etc.
- **Environment variables**: 
  - `DEBUG_ENDPOINTS_ENABLED=false` (disable in production)
  - `DEBUG_API_KEY=` (optional debug API key)
  - `DEBUG_ALLOWED_IPS=127.0.0.1,::1` (IP whitelist for debug endpoints)
- **Test security**: `python test_security_config.py`
