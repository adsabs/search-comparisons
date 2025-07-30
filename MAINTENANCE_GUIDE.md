# Search Comparisons Tool - Maintenance & Operations Guide

## 🎯 Critical System Components

### HIGH PRIORITY - Monitor Daily

#### 1. SearchService Orchestrator (`search_service.py`)
**Why Critical**: Core component that coordinates all search operations
- **Health Check**: `curl http://localhost:8001/api/health`
- **Key Metrics**: Response time, success rate, timeout frequency
- **Failure Impact**: Complete system failure - no search results from any engine

#### 2. Google Scholar Service (`scholar_service.py`)
**Why Critical**: Most fragile component due to HTML scraping
- **Warning Signs**: Empty Scholar results, parsing errors, 403/429 HTTP errors
- **Common Fixes**:
  ```bash
  # Update scholarly library
  pip install --upgrade scholarly
  
  # Rotate proxy servers (edit scholar_service.py)
  # Increase request delays
  ```
- **Emergency Bypass**: Disable Scholar in `SERVICE_CONFIG` if blocking other engines

#### 3. API Key Health
**Critical Keys**:
- **ADS_API_KEY**: Required for primary search functionality
- **WOS_API_KEY**: Optional but valuable for comparison
- **Monitoring**: Check quotas and expiration dates weekly

### MEDIUM PRIORITY - Monitor Weekly

#### 4. LLM Service (Query Intent)
**Why Important**: Powers natural language query transformation
- **Dependencies**: Ollama service, model availability
- **Health Check**: `curl http://localhost:11434/api/tags`
- **Fallback**: System functions without it, just no query transformation

#### 5. Cache Performance
**Why Important**: Affects response times and API quota usage
- **Target Hit Rate**: >70% for production workloads
- **Monitor**: `curl http://localhost:8001/api/admin/cache/stats`
- **Maintenance**: Clear cache if hit rate drops below 50%

## 🔧 Daily Operations Checklist

### Morning Health Check (5 minutes)
```bash
# 1. Verify all services are running
curl -s http://localhost:8001/health | jq .

# 2. Check error rates
curl -s http://localhost:8001/api/admin/errors

# 3. Test basic search functionality
curl -X POST http://localhost:8001/api/search \
  -H "Content-Type: application/json" \
  -d '{"query": "black holes", "sources": ["ads", "scholar"]}'

# 4. Verify cache performance
curl -s http://localhost:8001/api/admin/cache/stats | jq .
```

### If Any Check Fails
1. **Review logs**: `tail -50 backend.log`
2. **Restart services**: `./stop_servers.sh && ./startup_with_logs.sh`
3. **Check external dependencies**: API keys, Ollama service, internet connectivity

## 🚨 Emergency Response Procedures

### Complete System Down
**Symptoms**: Frontend won't load, backend unreachable
```bash
# Step 1: Force restart everything
pkill -f "uvicorn\|node"
./startup_with_logs.sh

# Step 2: Check for port conflicts
lsof -i :8001
lsof -i :3001

# Step 3: Verify environment
python3 -c "import app.main; print('Backend OK')"
cd frontend && npm run build
```

### Search Results Empty Across All Engines
**Symptoms**: All search engines return zero results
```bash
# Step 1: Test primary API directly
curl -H "Authorization: Bearer $ADS_API_KEY" \
  "https://api.adsabs.harvard.edu/v1/search/query?q=star&fl=title"

# Step 2: Check API key quotas
# Review ADS quota at: https://ui.adsabs.harvard.edu/user/account/status

# Step 3: Verify network connectivity
ping api.adsabs.harvard.edu
ping api.semanticscholar.org

# Step 4: Check firewall/proxy settings
export https_proxy=your_proxy_if_needed
```

### Google Scholar Completely Blocked
**Symptoms**: Scholar service returns 403 errors consistently
```bash
# Emergency fix: Disable Scholar temporarily
# Edit backend/app/services/search_service.py
# Comment out scholar from SERVICE_CONFIG

# Longer-term fix: Update proxy rotation
# Edit backend/app/services/scholar_service.py
# Add new proxy servers to PROXY_LIST

# Test from different IP:
curl -x proxy_server:port "https://scholar.google.com/scholar?q=test"
```

### Query Intent Service Down
**Symptoms**: "Analyze Intent" button fails or hangs
```bash
# Step 1: Check if Ollama is running
ps aux | grep ollama
curl http://localhost:11434/api/tags

# Step 2: Restart Ollama if needed
ollama serve &

# Step 3: Verify model availability
ollama list
# Should show phi:2.7b or qwen2:7b

# Step 4: Pull model if missing
ollama pull phi:2.7b
```

### Database Corruption/Locking
**Symptoms**: Judgments can't be saved, SQLite errors
```bash
# Step 1: Check for lock files
ls -la backend/app/data/
rm -f backend/app/data/*.db-wal backend/app/data/*.db-shm

# Step 2: Backup and repair
cp backend/app/data/app.db backend/app/data/app_backup_$(date +%Y%m%d).db
sqlite3 backend/app/data/app.db "PRAGMA integrity_check;"

# Step 3: If corrupted, restore from backup
# (Implement regular backups as preventive measure)
```

## 📊 Monitoring & Alerting Setup

### Key Metrics to Monitor

#### System Health Metrics
```bash
# Response time (should be <5 seconds for most queries)
curl -w "@curl-format.txt" -s -o /dev/null http://localhost:8001/api/health

# Memory usage (should stay <2GB for backend)
ps aux | grep uvicorn | awk '{print $6}'

# Disk usage (SQLite database growth)
du -h backend/app/data/app.db
```

#### Business Metrics
```bash
# Search success rate (should be >95%)
# Query volume per day
# Cache hit rate (should be >70%)
curl http://localhost:8001/api/admin/cache/stats

# Judgment submission rate
sqlite3 backend/app/data/app.db "SELECT COUNT(*) FROM judgments WHERE DATE(created_at) = DATE('now');"
```

#### Error Rate Monitoring
```bash
# API errors by type
curl http://localhost:8001/api/admin/errors

# Log analysis for patterns
grep "ERROR" backend.log | tail -20
grep "timeout" backend.log | wc -l
```

### Automated Health Checks
Create a monitoring script (`monitor.sh`):
```bash
#!/bin/bash

# Health check endpoint
if ! curl -f -s http://localhost:8001/health > /dev/null; then
    echo "ALERT: Backend health check failed" | mail -s "SearchComparisons Down" admin@example.com
fi

# Cache hit rate check
HIT_RATE=$(curl -s http://localhost:8001/api/admin/cache/stats | jq '.search_cache.hit_rate')
if (( $(echo "$HIT_RATE < 0.5" | bc -l) )); then
    echo "WARNING: Cache hit rate is $HIT_RATE" | mail -s "SearchComparisons Cache Issue" admin@example.com
fi

# Error rate check
ERROR_COUNT=$(curl -s http://localhost:8001/api/admin/errors | jq '.ads_api_timeout + .scholar_rate_limit')
if [ "$ERROR_COUNT" -gt 10 ]; then
    echo "WARNING: High error rate: $ERROR_COUNT errors" | mail -s "SearchComparisons Errors" admin@example.com
fi
```

Run via cron:
```bash
# Add to crontab (crontab -e)
*/5 * * * * /path/to/monitor.sh
```

## 🔄 Regular Maintenance Tasks

### Weekly Tasks (30 minutes)

#### API Key Management
```bash
# Check ADS API usage
curl -H "Authorization: Bearer $ADS_API_KEY" \
  "https://api.adsabs.harvard.edu/v1/accounts/user"

# Rotate keys if approaching limits
# Update environment variables
# Test with new keys
```

#### Performance Review
```bash
# Analyze slow queries from logs
grep "response_time" backend.log | awk '{print $NF}' | sort -n | tail -10

# Check database size growth
du -h backend/app/data/app.db

# Review error patterns
grep "ERROR" backend.log | cut -d' ' -f3- | sort | uniq -c | sort -nr
```

#### Google Scholar Health
```bash
# Test Scholar search manually
curl "https://scholar.google.com/scholar?q=test+query"

# Check if scholarly library needs updates
pip list | grep scholarly
pip show scholarly  # Check for newer versions

# Review Scholar-specific errors
grep "scholar" backend.log | grep "ERROR"
```

### Monthly Tasks (2 hours)

#### Dependency Updates
```bash
# Backend dependencies
pip list --outdated
pip install --upgrade scholarly httpx fastapi

# Frontend dependencies
cd frontend
npm outdated
npm update

# Security updates
pip audit
npm audit
```

#### Database Maintenance
```bash
# Analyze database growth
sqlite3 backend/app/data/app.db "SELECT COUNT(*) FROM judgments;"
sqlite3 backend/app/data/app.db "SELECT COUNT(*) FROM search_cache;"

# Archive old data if needed
sqlite3 backend/app/data/app.db "DELETE FROM search_cache WHERE created_at < datetime('now', '-30 days');"

# Vacuum database
sqlite3 backend/app/data/app.db "VACUUM;"
```

#### Performance Optimization
```bash
# Analyze cache effectiveness
curl http://localhost:8001/api/admin/cache/stats

# Review LLM model performance
# Consider upgrading to newer models
ollama list
ollama pull qwen2:7b  # If newer version available
```

### Quarterly Tasks (4 hours)

#### Full System Review
- Review all configuration settings
- Update documentation for any changes
- Performance benchmark against historical data
- Security audit of API keys and endpoints
- Backup and disaster recovery testing

#### Infrastructure Updates
- Operating system updates
- Python version upgrades (test in staging first)
- Node.js version upgrades
- SSL certificate renewal

## 🎛️ Configuration Management

### Environment Variables Reference
```bash
# Core Settings
ADS_API_KEY=your_ads_key                    # Required
WOS_API_KEY=your_wos_key                    # Optional
SEMANTIC_SCHOLAR_API_KEY=your_s2_key        # Optional

# LLM Settings
LLM_PROVIDER=ollama                         # ollama|openai|huggingface
LLM_MODEL_NAME=phi:2.7b                     # Model identifier
LLM_API_ENDPOINT=http://localhost:11434/api/generate
LLM_TEMPERATURE=0.3                         # Creativity level
LLM_MAX_TOKENS=2000                         # Response length limit

# Performance Settings
CACHE_TTL=3600                              # Cache lifetime (seconds)
CACHE_MAX_SIZE=1000                         # Max items in cache
REQUEST_TIMEOUT=30                          # API timeout (seconds)
MAX_CONCURRENT_REQUESTS=5                   # Rate limiting

# Security Settings
DEBUG_ENDPOINTS_ENABLED=false               # Disable in production
DEBUG_API_KEY=optional_debug_key            # For debug endpoints
DEBUG_ALLOWED_IPS=127.0.0.1,::1            # IP whitelist

# Database Settings
DATABASE_URL=sqlite:///app/data/app.db      # Database connection
DATABASE_POOL_SIZE=5                        # Connection pool
```

### Backup Strategy
```bash
# Daily automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/path/to/backups"

# Database backup
cp backend/app/data/app.db "$BACKUP_DIR/app_db_$DATE.db"

# Configuration backup
tar -czf "$BACKUP_DIR/config_$DATE.tar.gz" \
  backend/.env \
  frontend/.env \
  AGENT.md \
  *.md

# Code repository backup (if not using Git remotes)
git bundle create "$BACKUP_DIR/repo_$DATE.bundle" --all

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -name "*.db" -mtime +30 -delete
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +30 -delete
```

## 🐛 Common Issues & Solutions

### Issue: High Memory Usage
**Symptoms**: Backend process using >4GB RAM
**Causes**: Large cache, memory leaks, large result sets
**Solutions**:
```bash
# Clear caches
curl -X POST http://localhost:8001/api/admin/cache/clear

# Reduce cache size
export CACHE_MAX_SIZE=500

# Monitor for memory leaks
ps aux | grep uvicorn
# If memory keeps growing, restart service
```

### Issue: Slow Query Response
**Symptoms**: Searches taking >30 seconds
**Investigation**:
```bash
# Check which engine is slow
grep "response_time" backend.log | grep "engine:"

# Common slow engines and fixes:
# Google Scholar: Add delays, rotate proxies
# ADS: Check API quota, reduce concurrent requests
# Web of Science: Verify API key, check rate limits
```

### Issue: Frontend Build Failures
**Symptoms**: `npm run build` fails, TypeScript errors
**Solutions**:
```bash
# Clear node modules and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install

# Fix TypeScript errors
npm run type-check

# Check for version conflicts
npm ls --depth=0
```

### Issue: Certificate/SSL Errors
**Symptoms**: API calls fail with SSL verification errors
**Solutions**:
```bash
# Update certificates
curl -k https://api.adsabs.harvard.edu/v1/  # Test without verification

# Python SSL issues
pip install --upgrade certifi

# System certificate update (Ubuntu)
sudo apt-get update && sudo apt-get install ca-certificates
```

## 📈 Performance Optimization

### Database Optimization
```sql
-- Add indexes for common queries
CREATE INDEX idx_judgments_query ON judgments(query);
CREATE INDEX idx_judgments_created_at ON judgments(created_at);
CREATE INDEX idx_search_cache_key ON search_cache(cache_key);
CREATE INDEX idx_search_cache_created_at ON search_cache(created_at);
```

### Cache Tuning
```python
# Adjust cache settings based on usage patterns
CACHE_CONFIG = {
    "search_results": {
        "max_size": 1000,
        "ttl": 3600  # 1 hour
    },
    "llm_responses": {
        "max_size": 500,
        "ttl": 86400  # 24 hours (longer for stable queries)
    }
}
```

### API Rate Limiting
```python
# Implement adaptive rate limiting
class AdaptiveRateLimiter:
    def __init__(self):
        self.success_rate = 1.0
        self.base_delay = 1.0
    
    async def wait_if_needed(self):
        if self.success_rate < 0.8:  # If success rate drops
            delay = self.base_delay / self.success_rate
            await asyncio.sleep(delay)
```

This maintenance guide provides comprehensive procedures for keeping the Search Comparisons Tool running smoothly in production.
