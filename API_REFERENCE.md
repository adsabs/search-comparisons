# Search Comparisons API Reference

## 🔗 Quick Access

### Interactive Documentation
- **Swagger UI**: http://localhost:8001/api/docs - Interactive API explorer
- **ReDoc**: http://localhost:8001/api/redoc - Clean documentation view  
- **OpenAPI Schema**: http://localhost:8001/api/openapi.json - Machine-readable specification

### API Base URL
- **Local Development**: `http://localhost:8001`
- **Production**: `https://your-domain.com` (configure in deployment)

## 📋 Core Endpoints

### 🔍 Search Operations

#### Multi-Engine Search
```http
POST /api/search
Content-Type: application/json

{
  "query": "black hole mergers",
  "sources": ["ads", "scholar", "semantic_scholar"],
  "max_results": 20,
  "information_need": "Recent papers on gravitational wave detection"
}
```

**Response**:
```json
{
  "query": "black hole mergers",
  "rewritten_query": null,
  "engines": ["ads", "scholar", "semantic_scholar"],
  "results": {
    "ads": [...],
    "scholar": [...],
    "semantic_scholar": [...]
  },
  "stats": {
    "total_results": 45,
    "ndcg": {
      "ads_vs_scholar": 0.85,
      "ads_vs_semantic": 0.78
    },
    "jaccard": {
      "ads_vs_scholar": 0.23,
      "ads_vs_semantic": 0.31
    },
    "title_overlap": {
      "ads_vs_scholar": 8,
      "ads_vs_semantic": 12
    }
  }
}
```

#### Boost Experiment Search
```http
POST /api/experiments/boost
Content-Type: application/json

{
  "query": "exoplanets",
  "boost_config": {
    "citation_boost": 2.0,
    "recency_boost": 1.5,
    "recency_decay": 0.1,
    "doctype_boosts": {
      "article": 1.0,
      "inproceedings": 0.8,
      "phdthesis": 0.6
    },
    "field_weights": {
      "title": 3.0,
      "abstract": 1.0,
      "author": 2.0
    }
  }
}
```

### 🧠 Query Intent & Transformation

#### Transform Natural Language Query
```http
POST /api/intent-transform-query
Content-Type: application/json

{
  "query": "papers by Stephen Hawking about black holes"
}
```

**Response**:
```json
{
  "original_query": "papers by Stephen Hawking about black holes",
  "intent": "author_topic",
  "explanation": "Looking for papers by a specific author on a particular topic",
  "transformed_query": "(author:\"Hawking, S\" OR author:\"Hawking, Stephen\") AND abs:\"black holes\"",
  "confidence": 0.95
}
```

### 📊 Relevance Judgments

#### Submit Judgments
```http
POST /api/judgements
Content-Type: application/json

{
  "query": "dark matter detection",
  "judgements": [
    {
      "record_title": "Direct Detection of Dark Matter",
      "record_source": "ads",
      "judgement_score": 1.0,
      "judgement_note": "Highly relevant to the query"
    }
  ],
  "rater_id": "evaluator_001",
  "information_need": "Recent experimental approaches to dark matter detection"
}
```

#### Batch Submit Judgments
```http
POST /api/judgements/batch
Content-Type: application/json

{
  "judgements": [
    {
      "query": "gravitational waves",
      "record_title": "LIGO Detection Results",
      "record_source": "ads",
      "judgement_score": 1.0,
      "rater_id": "expert_1"
    },
    {
      "query": "gravitational waves", 
      "record_title": "Theoretical Wave Predictions",
      "record_source": "scholar",
      "judgement_score": 0.67,
      "rater_id": "expert_1"
    }
  ]
}
```

#### Retrieve Judgments
```http
GET /api/judgements?query=gravitational%20waves&rater_id=expert_1
```

### 🏥 Health & Monitoring

#### System Health Check
```http
GET /api/health
```

**Response**:
```json
{
  "status": "ok",
  "version": "1.0.0",
  "environment": "local",
  "services": {
    "ads": "healthy",
    "scholar": "healthy", 
    "semantic_scholar": "healthy",
    "llm": "healthy"
  }
}
```

#### Cache Statistics (Admin)
```http
GET /api/debug/cache/stats
```

**Response**:
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

## 🔧 Debug & Development Endpoints

### Test Individual Search Engines
```http
GET /api/debug/search/ads?q=black%20holes&rows=5
GET /api/debug/search/scholar?q=exoplanets&rows=5
GET /api/debug/search/semantic_scholar?q=machine%20learning&rows=5
```

### Paper Detail Lookup
```http
GET /api/debug/paper/10.1103/PhysRevLett.116.061102
```

### Service Connectivity Test
```http
GET /api/debug/ping/ads
GET /api/debug/ping/scholar
GET /api/debug/ping/semantic_scholar
```

## 📝 Data Models

### SearchResult
```json
{
  "id": "2016PhRvL.116f1102A",
  "title": "Observation of Gravitational Waves from a Binary Black Hole Merger",
  "authors": ["B. P. Abbott", "R. Abbott", "..."],
  "abstract": "On September 14, 2015 at 09:50:45 UTC...",
  "publication_date": "2016-02-11",
  "url": "https://doi.org/10.1103/PhysRevLett.116.061102",
  "citation_count": 4829,
  "source": "ads",
  "doctype": "article",
  "collection": "physics",
  "refereed": true,
  "boost_score": 1.45
}
```

### BoostConfig
```json
{
  "citation_boost": 2.0,
  "recency_boost": 1.5,
  "recency_decay": 0.1,
  "doctype_boosts": {
    "article": 1.0,
    "inproceedings": 0.8,
    "phdthesis": 0.6,
    "book": 0.4
  },
  "collection_boosts": {
    "astronomy": 1.0,
    "physics": 0.9,
    "general": 0.5
  },
  "field_weights": {
    "title": 3.0,
    "abstract": 1.0,
    "author": 2.0,
    "year": 0.5,
    "keyword": 1.5
  },
  "boost_weights": {
    "citation": 0.3,
    "recency": 0.2,
    "doctype": 0.2,
    "collection": 0.2,
    "refereed": 0.1
  },
  "refereed_boost": 1.2
}
```

## 🚦 Rate Limiting

### Default Limits
- **Search endpoints**: 30 requests/minute
- **LLM endpoints**: 10 requests/minute  
- **General endpoints**: 60 requests/minute
- **Debug endpoints**: IP whitelist + optional API key

### Headers
Rate limit information is returned in response headers:
```
X-RateLimit-Limit: 30
X-RateLimit-Remaining: 25
X-RateLimit-Reset: 1609459200
```

## 🔐 Authentication

### Development
No authentication required for local development.

### Production
- Debug endpoints: IP whitelist + optional API key
- Set `DEBUG_API_KEY` environment variable
- Configure `DEBUG_ALLOWED_IPS` for access control

## ❌ Error Responses

### Standard Error Format
```json
{
  "status_code": 400,
  "message": "Invalid request parameters",
  "details": "The 'query' field is required",
  "request_id": "uuid-here"
}
```

### Common HTTP Status Codes
- `200` - Success
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (missing/invalid API key)
- `403` - Forbidden (rate limited or IP blocked)
- `404` - Not Found (endpoint doesn't exist)
- `422` - Validation Error (invalid data format)
- `429` - Too Many Requests (rate limit exceeded)
- `500` - Internal Server Error
- `503` - Service Unavailable (external API down)

## 📚 SDK Examples

### Python
```python
import requests

# Basic search
response = requests.post('http://localhost:8001/api/search', json={
    'query': 'dark matter detection',
    'sources': ['ads', 'scholar'],
    'max_results': 10
})
results = response.json()

# Query transformation
response = requests.post('http://localhost:8001/api/intent-transform-query', json={
    'query': 'papers by Einstein about relativity'
})
transformed = response.json()
print(f"Original: {transformed['original_query']}")
print(f"Transformed: {transformed['transformed_query']}")
```

### JavaScript/Node.js
```javascript
const axios = require('axios');

async function searchPapers(query) {
  try {
    const response = await axios.post('http://localhost:8001/api/search', {
      query: query,
      sources: ['ads', 'scholar', 'semantic_scholar'],
      max_results: 20
    });
    return response.data;
  } catch (error) {
    console.error('Search failed:', error.response?.data || error.message);
  }
}

// Usage
searchPapers('machine learning astronomy').then(results => {
  console.log(`Found ${results.stats.total_results} papers`);
  console.log(`NDCG score: ${results.stats.ndcg.ads_vs_scholar}`);
});
```

### cURL Examples
```bash
# Search across multiple engines
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "exoplanet detection",
    "sources": ["ads", "scholar"],
    "max_results": 15
  }'

# Transform natural language query
curl -X POST http://localhost:8001/api/intent-transform-query \
  -H "Content-Type: application/json" \
  -d '{"query": "recent papers on JWST observations"}'

# Submit relevance judgment
curl -X POST http://localhost:8001/api/judgements \
  -H "Content-Type: application/json" \
  -d '{
    "query": "stellar evolution",
    "judgements": [{
      "record_title": "The Evolution of Massive Stars",
      "record_source": "ads",
      "judgement_score": 1.0,
      "judgement_note": "Excellent overview paper"
    }],
    "rater_id": "astronomer_1"
  }'
```

## 🔍 Advanced Usage

### Custom Boost Configurations
```python
# Optimize for recent, highly-cited papers
boost_config = {
    "citation_boost": 3.0,        # Strong citation preference
    "recency_boost": 2.0,         # Recent papers preferred
    "recency_decay": 0.2,         # Slow decay over time
    "doctype_boosts": {
        "article": 1.0,           # Journal articles
        "inproceedings": 0.6,     # Conference papers
        "preprint": 0.8           # Preprints
    },
    "refereed_boost": 1.5         # Peer-reviewed boost
}

response = requests.post('http://localhost:8001/api/experiments/boost', json={
    'query': 'gravitational wave detection',
    'boost_config': boost_config
})
```

### Batch Processing
```python
# Process multiple queries efficiently
queries = [
    "dark matter detection",
    "exoplanet atmospheres", 
    "stellar evolution models"
]

results = []
for query in queries:
    response = requests.post('http://localhost:8001/api/search', json={
        'query': query,
        'sources': ['ads', 'semantic_scholar'],
        'max_results': 10
    })
    results.append(response.json())

# Analyze comparative performance
for i, result in enumerate(results):
    print(f"Query: {queries[i]}")
    print(f"NDCG: {result['stats']['ndcg']['ads_vs_semantic_scholar']}")
    print(f"Title Overlap: {result['stats']['title_overlap']['ads_vs_semantic_scholar']}")
```

For more examples and integration guides, see the [ONBOARDING.md](ONBOARDING.md) documentation.
