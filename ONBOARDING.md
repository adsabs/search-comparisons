# Search Comparisons Tool - Complete Onboarding Guide

## 🎯 Executive Summary

The Search Comparisons Tool is a research-grade web application that enables side-by-side comparison of academic search results across multiple scholarly databases. Built for NASA ADS/SciX, it serves three primary audiences:

- **Relevance Evaluators**: Collect quality judgments on search results
- **SciX Engineers**: Test ranking algorithms and boost configurations
- **Research Scientists**: Experiment with query transformations and similarity algorithms

## 🚀 Quick 5-Minute Setup

### Prerequisites Check
```bash
# Verify Python 3.8+ is installed
python3 --version

# Verify Node.js is installed  
node --version

# Check if Ollama is running (for query intent features)
curl -s http://localhost:11434/api/tags
```

### One-Command Startup
```bash
cd /path/to/search-comparisons
./startup_with_logs.sh
```

**Access URLs:**
- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8001  
- **API Documentation**: http://localhost:8001/api/docs

### First-Time Usage Test
1. Open http://localhost:3001
2. Navigate to **Experiments → Relevance Judgements**
3. Enter test query: `"black hole merger"`
4. Click **Search** button
5. Verify results appear in all three columns

## 📋 Complete Setup Checklist

### System Requirements
- [ ] **Operating System**: Linux/macOS/Windows with WSL
- [ ] **Python**: 3.8 or higher with pip
- [ ] **Node.js**: 16+ with npm/pnpm
- [ ] **Memory**: 4GB+ RAM (8GB+ recommended for LLM features)
- [ ] **Disk Space**: 2GB for dependencies, 10GB+ for LLM models

### API Keys Configuration
- [ ] **ADS_API_KEY**: Required for NASA ADS search ([Get key here](https://ui.adsabs.harvard.edu/user/settings/token))
- [ ] **WOS_API_KEY**: Optional, for Web of Science integration
- [ ] **SEMANTIC_SCHOLAR_API_KEY**: Optional, but recommended for higher rate limits

### Optional LLM Setup (for Query Intent features)
- [ ] **Install Ollama**: `curl -L https://ollama.ai/install.sh | sh`
- [ ] **Pull model**: `ollama pull phi:2.7b` (lightweight) or `ollama pull qwen2:7b` (better quality)
- [ ] **Start service**: `ollama serve &`

### Environment Variables Setup
Create `backend/.env`:
```bash
# Required
ADS_API_KEY=your_ads_api_key_here

# Optional but recommended
WOS_API_KEY=your_wos_key_here
SEMANTIC_SCHOLAR_API_KEY=your_semantic_scholar_key

# LLM Configuration (defaults shown)
LLM_PROVIDER=ollama
LLM_MODEL_NAME=phi:2.7b
LLM_API_ENDPOINT=http://localhost:11434/api/generate

# Cache Settings
CACHE_TTL=3600
CACHE_MAX_SIZE=1000

# Debug (set to false in production)
DEBUG_ENDPOINTS_ENABLED=false
```

## 🏗️ Architecture Deep Dive

### High-Level Data Flow
```
User Query → Frontend (React) → Backend (FastAPI) → Multiple Search APIs
                ↓
Query Intent Service (LLM) → Enhanced Query → Search Results
                ↓
Comparison Service → Metrics (NDCG, Jaccard, Title Overlap)
                ↓
Boost Service → Re-ranked Results → Frontend Display
```

### Critical Backend Services

#### 1. Search Service (`search_service.py`) - **CORE**
**Purpose**: Orchestrates all search operations
- Manages parallel requests to multiple engines
- Handles timeouts and fallback mechanisms  
- Coordinates caching and response merging
- **Maintenance Priority**: HIGH - this breaks everything if it fails

#### 2. Individual Engine Services
- **ADS Service**: Primary academic database for astronomy/physics
- **Scholar Service**: Google Scholar integration (FRAGILE - uses scraping)
- **Semantic Scholar Service**: Computer science focus
- **Web of Science Service**: Broad academic coverage

#### 3. Query Intent Service - **AI COMPONENT**
**Purpose**: Transforms natural language to precise search syntax
- Uses local LLM models (Ollama) for privacy
- Implements few-shot learning with curated examples
- **Models supported**: phi:2.7b (fast), qwen2:7b (accurate), custom options

#### 4. Cache Service
**Purpose**: Performance optimization
- LRU cache with TTL for search results
- Separate cache for LLM query transformations
- **Monitor**: Cache hit rates should be >70% in production

### Frontend Architecture (React + TypeScript)

#### Key Components:
- **App.tsx**: Main routing and state management
- **RelevanceJudgements.tsx**: Three-column result comparison interface
- **BoostExperiment.tsx**: Algorithm testing with ranking sliders
- **QueryIntent.tsx**: Natural language query transformation
- **SimilarityTests.tsx**: Future embeddings comparison framework

#### State Management:
- Uses React hooks (no Redux)
- Client-side title overlap calculation for accuracy
- Manual judgment scores stored locally until submission

## 🔧 Development Workflows

### Adding a New Search Engine

**Example: Adding arXiv Search**

1. **Create Service Module** (`services/arxiv_service.py`):
```python
import asyncio
import logging
from typing import List
import httpx
from app.api.search_models import SearchResult

class ArxivService:
    def __init__(self):
        self.base_url = "http://export.arxiv.org/api/query"
        self.timeout = 30.0
    
    async def get_arxiv_results(self, query: str, max_results: int = 20) -> List[SearchResult]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                params = {
                    "search_query": f"all:{query}",
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "relevance"
                }
                response = await client.get(self.base_url, params=params)
                response.raise_for_status()
                return self._parse_atom_feed(response.text)
        except Exception as e:
            logging.error(f"ArXiv search failed: {e}")
            return []
    
    def _parse_atom_feed(self, xml_content: str) -> List[SearchResult]:
        # Parse arXiv atom feed and return SearchResult objects
        # Implementation details...
        pass
```

2. **Register in SearchService** (`services/search_service.py`):
```python
SERVICE_CONFIG = {
    "arxiv": {
        "priority": 4,
        "timeout": 30.0,
        "fallback_available": False
    },
    # ... existing configs
}
```

3. **Add Frontend Support** (`types/search.ts`):
```typescript
export enum SearchEngine {
    ADS = "ads",
    SCHOLAR = "scholar",
    ARXIV = "arxiv",  // Add this line
    // ... existing engines
}
```

### Customizing Query Intent Examples

**Location**: `backend/app/services/query_intent/llm_service.py`

**Pattern to follow**:
```python
Original: "papers about gravitational waves by LIGO"
Intent: author_topic
Explanation: Looking for LIGO collaboration papers on gravitational waves
Transformed: (author:"LIGO" OR author:"LIGO Collaboration") AND abs:"gravitational waves"
```

**Testing new patterns**:
```bash
curl -X POST http://localhost:8001/api/intent-transform-query \
    -H "Content-Type: application/json" \
    -d '{"query": "your test query here"}'
```

### Performance Monitoring Setup

**Cache Metrics** (`/api/admin/cache/stats`):
```json
{
  "search_cache": {
    "size": 156,
    "hits": 892,
    "misses": 234,
    "hit_rate": 0.79
  },
  "llm_cache": {
    "size": 45,
    "hits": 123,
    "misses": 12,
    "hit_rate": 0.91
  }
}
```

**Error Tracking** (`/api/admin/errors`):
```json
{
  "ads_api_timeout": 3,
  "scholar_rate_limit": 12,
  "llm_model_error": 0
}
```

## 🔍 Common Maintenance Tasks

### Daily Monitoring
```bash
# Check service health
curl http://localhost:8001/health

# Monitor cache performance
curl http://localhost:8001/api/admin/cache/stats

# Check error rates
curl http://localhost:8001/api/admin/errors
```

### Weekly Tasks
- **API Key Rotation**: Check ADS/WOS key validity and usage quotas
- **Model Updates**: Update Ollama models if available (`ollama pull qwen2:7b`)
- **Log Analysis**: Review application logs for recurring errors
- **Database Cleanup**: Archive old relevance judgments if database grows large

### Monthly Tasks
- **Dependency Updates**: Update Python packages and Node.js dependencies
- **Performance Review**: Analyze response times and optimize slow queries
- **Security Audit**: Review API endpoints and access controls

### Google Scholar Maintenance (CRITICAL)
**Why it's fragile**: Scholar service uses HTML scraping, which breaks when Google changes their layout.

**Warning signs**:
- Empty results from Scholar engine
- Parsing errors in logs
- Blocked requests (403/429 errors)

**Immediate fixes**:
1. **Update scholarly library**: `pip install --upgrade scholarly`
2. **Rotate proxy servers**: Update proxy list in `scholar_service.py`
3. **Adjust rate limiting**: Increase delays between requests
4. **Update CSS selectors**: Fix HTML parsing in `_parse_scholar_response()`

## 🎯 User Onboarding by Role

### For Relevance Evaluators

**Goal**: Collect quality judgments to improve search algorithms

**Workflow**:
1. **Setup**: No technical setup required - just access the web interface
2. **Navigate**: Go to **Experiments → Relevance Judgements**
3. **Search**: Enter your query and description of information need
4. **Evaluate**: Score papers 0-3 based on relevance to your need
5. **Submit**: Click "Submit Judgements" to store in database
6. **Export**: Use "Export Judgements" for comprehensive reports

**Best Practices**:
- Always fill in the "Information Need" field
- Read abstracts before scoring (click the ▼ button)
- Be consistent with your scoring scale
- Score at least the first 10 results per engine
- Use the notes field for edge cases

### For SciX Engineers

**Goal**: Test search algorithm changes and boost configurations

**Workflow**:
1. **Baseline**: Record current performance with default settings
2. **Experiment**: Adjust boost controls (citation, recency, document type)
3. **Compare**: Use NDCG@10 scores to measure improvement
4. **Iterate**: Test multiple configurations and compare results
5. **Deploy**: Implement best-performing settings in production

**Key Features**:
- **Boost Controls**: 15+ different ranking factors to adjust
- **Real-time NDCG**: Immediate feedback on ranking quality  
- **Document Type Filtering**: Remove or boost specific publication types
- **Collection Weights**: Adjust relative importance of different databases

### For Research Scientists

**Goal**: Prototype new algorithms and test research hypotheses

**Workflow**:
1. **Query Intent**: Test natural language query transformations
2. **Similarity Tests**: Compare different paper similarity approaches
3. **Algorithm Development**: Integrate new services via the plugin architecture
4. **Evaluation**: Use the judgment database for ground truth validation

**Extension Points**:
- **New Search Engines**: Add services by following the template pattern
- **Custom LLM Models**: Train domain-specific models for query understanding
- **Similarity Algorithms**: Implement new approaches in `SimilarityTests` component
- **Evaluation Metrics**: Add custom metrics to `comparison_service.py`

## 🚨 Troubleshooting Playbook

### Issue: Frontend Won't Load
**Symptoms**: Blank page, console errors about API connection
**Quick Fix**:
```bash
# Check if backend is running
curl http://localhost:8001/health

# If not running, restart everything
./stop_servers.sh
./startup_with_logs.sh
```

### Issue: No Search Results
**Symptoms**: Empty results from all engines
**Investigation Steps**:
1. Check API keys: `curl -H "Authorization: Bearer $ADS_API_KEY" https://api.adsabs.harvard.edu/v1/search`
2. Check internet connectivity: `ping api.adsabs.harvard.edu`
3. Review logs: `tail -f backend.log`

### Issue: Query Intent Not Working
**Symptoms**: "Analyze Intent" button does nothing or shows errors
**Quick Fix**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve &

# Pull required model
ollama pull phi:2.7b
```

### Issue: Slow Performance
**Symptoms**: Searches take >30 seconds
**Investigation**:
```bash
# Check cache hit rate (should be >60%)
curl http://localhost:8001/api/admin/cache/stats

# Check external API response times in logs
grep "response_time" backend.log | tail -20
```

**Quick Fixes**:
- Clear cache: `curl -X POST http://localhost:8001/api/admin/cache/clear`
- Reduce concurrent requests by adjusting semaphores in `search_service.py`
- Switch to lighter LLM model: `export LLM_MODEL_NAME=phi:2.7b`

### Issue: Database Locked
**Symptoms**: Error saving judgments
**Quick Fix**:
```bash
# Check for multiple processes
lsof app.db

# Kill conflicting processes and restart
./stop_servers.sh
./startup_with_logs.sh
```

## 📊 Production Deployment Checklist

### Security Configuration
- [ ] Set `DEBUG_ENDPOINTS_ENABLED=false`
- [ ] Configure proper CORS origins (no wildcards)
- [ ] Use HTTPS for all external communications
- [ ] Rotate API keys regularly
- [ ] Set up firewall rules for port access

### Performance Optimization
- [ ] Use PostgreSQL instead of SQLite for production
- [ ] Set up Redis for distributed caching
- [ ] Configure load balancer for multiple backend instances
- [ ] Enable gzip compression
- [ ] Set up CDN for static assets

### Monitoring & Alerting
- [ ] Set up health check endpoint monitoring
- [ ] Configure alerts for API key quota exhaustion
- [ ] Monitor cache hit rates and performance metrics
- [ ] Set up log aggregation (ELK stack recommended)
- [ ] Configure error tracking (Sentry or similar)

### Backup & Recovery
- [ ] Automated database backups
- [ ] API key backup and rotation procedures
- [ ] Code repository backup
- [ ] Documentation backup and versioning

## 🎓 Learning Resources

### Code Architecture
- **Start Here**: [`AGENT.md`](AGENT.md) - Contains all development patterns
- **Core Logic**: [`search_service.py`](backend/app/services/search_service.py) - Main orchestrator
- **Query Processing**: [`query_intent/llm_service.py`](backend/app/services/query_intent/llm_service.py) - AI component

### API Documentation
- **[Complete API Reference](API_REFERENCE.md)** - Comprehensive guide with examples
- **Interactive Swagger UI**: http://localhost:8001/api/docs (when running)
- **ReDoc Documentation**: http://localhost:8001/api/redoc (alternative view)
- **OpenAPI Schema**: http://localhost:8001/api/openapi.json (machine-readable)
- **Schema Reference**: [`backend/app/api/`](backend/app/api/) directory

#### Key API Endpoints
- **Search**: `POST /api/search` - Multi-engine search with comparison metrics
- **Query Intent**: `POST /api/intent-transform-query` - LLM-powered query transformation
- **Boost Experiments**: `POST /api/experiments/boost` - Algorithm testing with ranking adjustments
- **Judgements**: `POST /api/judgements` - Relevance judgment submission
- **Health**: `GET /api/health` - System health monitoring
- **Debug**: `GET /api/debug/*` - Development and troubleshooting endpoints

📖 **For detailed examples and integration guides, see [API_REFERENCE.md](API_REFERENCE.md)**

### Research Papers & Context
- **Search Evaluation**: NDCG, Jaccard similarity, title overlap metrics
- **Query Understanding**: Few-shot learning, prompt engineering
- **Academic Search**: ADS database structure, citation analysis

## 💡 Advanced Configuration

### Multiple LLM Providers
```bash
# OpenAI Setup
export LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-...
export LLM_MODEL_NAME=gpt-3.5-turbo

# HuggingFace Setup  
export LLM_PROVIDER=huggingface
export HF_API_TOKEN=hf_...
export LLM_MODEL_NAME=microsoft/DialoGPT-medium
```

### Custom Search Engine Integration
See the "Adding a New Search Engine" section above for step-by-step instructions.

### Database Migration (SQLite to PostgreSQL)
```python
# Update core/config.py
DATABASE_URL = "postgresql://user:password@localhost/searchdb"

# Install dependencies
pip install psycopg2-binary

# Run migration
alembic upgrade head
```

This onboarding guide provides everything needed for new team members to understand, deploy, maintain, and extend the Search Comparisons Tool effectively.
