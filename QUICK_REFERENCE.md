# Search Comparisons Tool - Quick Reference

## For Relevance Judgment Users

### Starting a Search Session
1. Open http://localhost:3001
2. Click on Experiments tab
3. Stay on the 'Relevance Judgements' tab
4. Type in your search query
5. Write in your information need (e.g., if your query is Jarmak and your information need is papers by Stephanie Jarmak or your query is landslides and your information need is recent and review papers on landslides)
6. Select 'show previous judgements' if you would like to see how others have judged the returned results if they are available in the database
7. Click "Search"
8. The returned results will show records from the ADS API on the left, the middle will return results after you run a 'boost experiment' (not necessary for relevance judgements unless testing boost changes), and you can select a comparison search engine to display on the right (Google Scholar, Web of Science, Semantic Scholar, or eventually a dev endpoint)

### Rating Results
- **3**: Perfectly matches information need
- **2**: Relevant but not what you would like to see in the top 5
- **1**: Marginally relevant
- **0**: Not relevant

### Best Practices
- Judge at least top 10 results from ADS/SciX (if comparing with the dev endpoint or other search engines then provide judgements for those results as well to compare NCDG scores)
- Add notes for additional information about your ratings where appropriate
- Include an information need


## For Developers

### Local Development Setup
```bash
# Backend only
cd backend && python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8001

# Frontend only  
cd frontend && pnpm install && pnpm dev

# Full stack with startup script
./start_local.sh
```

### Key Commands
- **Test**: `pytest backend/tests/`
- **Lint**: `ruff check backend/` or `black backend/`
- **Format**: `black backend/`

### Adding a New Search Engine
1. Create `services/your_engine_service.py`
2. Register in `main.py` and `SearchService`
3. Add to frontend `SearchEngine` enum
4. Update `SearchEngineSelector.tsx`

### Common File Locations
- API routes: `backend/app/routes/`
- Services: `backend/app/services/`
- Frontend components: `frontend/src/components/`
- API types: `frontend/src/types/`

## For Scientists

### Key API Endpoints
```bash
# Search comparison
POST /api/search/compare
{
  "query": "exoplanet atmospheres",
  "sources": ["ads", "scholar"],
  "boost_config": {"citation_boost": 1.5}
}

# Query transformation
POST /api/query-intent/transform?query=machine%20learning

# Get judgments
GET /api/quepid/judgments/{case_id}?query=exoplanet
```

### Common Boost Configurations
```json
{
  "citation_boost": 1.5,
  "recency_boost": 0.8,
  "doctype_boosts": {"article": 1.0, "phdthesis": 0.7},
  "adsQueryFields": {"title": 50, "author": 30}
}
```

### Metrics Interpretation
- **nDCG@10**: 0.8+ excellent, 0.6-0.8 good, 0.4-0.6 fair, <0.4 poor
- **Precision@10**: Fraction of relevant results in top 10
- **Jaccard**: 0.3+ high overlap, 0.1-0.3 moderate, <0.1 low overlap

### Python Example for Batch Testing
```python
import requests

config = {
    "query": "neutron stars",
    "sources": ["ads", "scholar"],
    "metrics": ["ndcg@10", "precision@10"],
    "boost_config": {"citation_boost": 1.2}
}

response = requests.post("http://localhost:8001/api/search/compare", json=config)
data = response.json()
print(f"ADS nDCG: {data['comparison']['ndcg@10']['ads']}")
```

## Common Troubleshooting

### API Issues
```bash
# Check health
curl http://localhost:8001/health

# Check cache stats
curl http://localhost:8001/api/admin/cache/stats

# Clear cache
curl -X POST http://localhost:8001/api/admin/cache/clear
```

### Frontend Issues
```bash
# Check environment
cat frontend/.env
# Should have: REACT_APP_API_URL=http://localhost:8001

# Restart frontend
cd frontend && pnpm dev
```

### External API Failures
- Check API keys in `backend/.env`
- Verify rate limits not exceeded
- Check service status pages
- Review logs in `backend/logs/app.log`

### Performance Issues
- Check cache hit rate
- Monitor external API response times
- Reduce concurrent requests if rate-limited
- Consider pagination for large result sets

## Environment Variables

### Required
```bash
ADS_API_KEY=your_ads_key
WEB_OF_SCIENCE_API_KEY=your_wos_key
```

### Optional
```bash
LOG_LEVEL=INFO
CACHE_TTL_SECONDS=3600
OLLAMA_BASE_URL=http://localhost:11434
REACT_APP_API_URL=http://localhost:8001
```

## Service URLs
- **Frontend**: http://localhost:3001
- **Backend API**: http://localhost:8001
- **API Docs**: http://localhost:8001/docs
- **Ollama LLM**: http://localhost:11434
- **Health Check**: http://localhost:8001/health

## Log Locations
- **Application logs**: `backend/logs/app.log`
- **Docker logs**: `docker-compose logs [service_name]`
- **Frontend logs**: Browser console (F12)

