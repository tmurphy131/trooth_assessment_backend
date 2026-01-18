# T[root]H Backend Scaling Guide

> Based on load test results from January 17, 2026
> Current baseline: ~50 concurrent users with 1 vCPU, 512Mi RAM, default Cloud SQL

## Current Configuration (Supports ~50 Concurrent Users)

```
Cloud Run:
- CPU: 1 vCPU
- Memory: 512Mi
- Max Instances: default (auto)

Cloud SQL (app-pg / app-pg-dev):
- Instance: db-f1-micro (or similar)
- Max Connections: ~25-50 (default)
```

**Key Bottleneck Identified:** PostgreSQL connection pool exhausts before CPU/memory limits are reached.

---

## 📈 Tier 1: 50-100 Concurrent Users

### When to upgrade
- You have 200-400 daily active users
- Users report occasional slowness during peak hours
- Seeing intermittent "connection refused" errors in logs

### Actions Required

#### 1. Increase Cloud SQL Connections
```bash
# For dev
gcloud sql instances patch app-pg-dev \
  --database-flags=max_connections=100

# For production
gcloud sql instances patch app-pg \
  --database-flags=max_connections=100
```

#### 2. Increase Cloud Run Memory
```bash
# Dev
gcloud run services update trooth-backend-dev \
  --region=us-east4 \
  --memory=1Gi

# Production
gcloud run services update trooth-backend \
  --region=us-east4 \
  --memory=1Gi
```

#### 3. Configure SQLAlchemy Pool (in code)
Update `app/db.py`:
```python
engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=300
)
```

### Estimated Monthly Cost Increase
- Cloud SQL: +$5-10/month
- Cloud Run: +$5-15/month (usage-based)

---

## 📈 Tier 2: 100-200 Concurrent Users

### When to upgrade
- You have 500-1000 daily active users
- Peak response times exceeding 2 seconds
- Multiple mentors running group sessions simultaneously

### Actions Required

#### 1. Upgrade Cloud SQL Instance
```bash
# Upgrade to db-g1-small (more CPU, memory)
gcloud sql instances patch app-pg \
  --tier=db-g1-small \
  --database-flags=max_connections=150
```

#### 2. Increase Cloud Run Resources
```bash
gcloud run services update trooth-backend \
  --region=us-east4 \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=1
```

#### 3. Add Connection Pooling (PgBouncer)
Deploy PgBouncer as a sidecar or separate service:
```yaml
# Option A: Cloud Run sidecar (recommended)
# Add to your Dockerfile or use multi-container setup

# Option B: Separate Cloud Run service
# Deploy PgBouncer container, point backend to it
```

#### 4. Enable Cloud CDN for Static Assets
If serving any static content, enable CDN caching.

### Estimated Monthly Cost Increase
- Cloud SQL: +$25-40/month (db-g1-small)
- Cloud Run: +$20-40/month
- Total: ~$50-80/month additional

---

## 📈 Tier 3: 200-500 Concurrent Users

### When to upgrade
- You have 1000-2500 daily active users
- Running marketing campaigns driving traffic spikes
- Multiple churches/organizations using the platform

### Actions Required

#### 1. Upgrade to High-Memory Cloud SQL
```bash
gcloud sql instances patch app-pg \
  --tier=db-custom-2-4096 \
  --database-flags=max_connections=300
```

#### 2. Implement Read Replicas
```bash
# Create read replica for heavy read operations
gcloud sql instances create app-pg-replica \
  --master-instance-name=app-pg \
  --region=us-east4
```

Update code to route reads to replica:
```python
# Use separate engines for read/write
read_engine = create_engine(READ_REPLICA_URL)
write_engine = create_engine(PRIMARY_URL)
```

#### 3. Scale Cloud Run Horizontally
```bash
gcloud run services update trooth-backend \
  --region=us-east4 \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=2 \
  --max-instances=10 \
  --concurrency=80
```

#### 4. Implement Redis Caching
Deploy Redis (Cloud Memorystore) for:
- Session caching
- Template caching (assessment templates don't change often)
- Rate limit state

```bash
gcloud redis instances create trooth-cache \
  --size=1 \
  --region=us-east4 \
  --redis-version=redis_6_x
```

#### 5. Move AI Scoring to Background Queue
Replace `BackgroundTasks` with proper queue:
- Deploy Cloud Tasks or Pub/Sub
- Process AI scoring asynchronously
- Prevents long-running requests from blocking

### Estimated Monthly Cost Increase
- Cloud SQL: +$80-120/month
- Cloud Run: +$50-100/month
- Redis: +$35/month
- Total: ~$165-255/month additional

---

## 📈 Tier 4: 500-1000 Concurrent Users

### When to upgrade
- You have 2500-5000 daily active users
- Platform is revenue-generating at scale
- Need enterprise-level reliability

### Actions Required

#### 1. Production-Grade Cloud SQL
```bash
gcloud sql instances patch app-pg \
  --tier=db-custom-4-8192 \
  --availability-type=REGIONAL \
  --database-flags=max_connections=500
```

#### 2. Multi-Region Deployment
Deploy Cloud Run in multiple regions:
```bash
# US East
gcloud run deploy trooth-backend \
  --region=us-east4 ...

# US West (for west coast users)
gcloud run deploy trooth-backend \
  --region=us-west1 ...
```

Use Cloud Load Balancing to route traffic.

#### 3. Dedicated AI Scoring Workers
```bash
# Deploy separate Cloud Run service for AI scoring
gcloud run deploy trooth-ai-worker \
  --region=us-east4 \
  --memory=4Gi \
  --cpu=2 \
  --no-allow-unauthenticated
```

#### 4. Implement Database Sharding (if needed)
Consider sharding by organization/church if data isolation is needed.

#### 5. Enhanced Monitoring
- Set up Cloud Monitoring dashboards
- Configure alerting policies
- Implement distributed tracing (Cloud Trace)

```bash
# Example alert policy
gcloud alpha monitoring policies create \
  --display-name="High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-filter='resource.type="cloud_run_revision"' \
  --notification-channels=...
```

### Estimated Monthly Cost Increase
- Cloud SQL (HA): +$200-300/month
- Cloud Run (multi-region): +$150-250/month
- Redis (larger): +$70/month
- Load Balancer: +$20/month
- Monitoring: +$20/month
- Total: ~$460-660/month additional

---

## 📈 Tier 5: 1000+ Concurrent Users

### When to upgrade
- You have 5000+ daily active users
- Enterprise/white-label deployments
- SLA requirements (99.9%+ uptime)

### Actions Required

#### 1. Enterprise Cloud SQL
```bash
gcloud sql instances patch app-pg \
  --tier=db-custom-8-32768 \
  --availability-type=REGIONAL \
  --enable-point-in-time-recovery \
  --backup-start-time=02:00 \
  --database-flags=max_connections=1000
```

#### 2. Kubernetes Migration (Optional)
Consider migrating to GKE for:
- Fine-grained resource control
- Custom autoscaling policies
- Service mesh (Istio) for observability

#### 3. Microservices Architecture
Split monolith into services:
- `auth-service` - Authentication/user management
- `assessment-service` - Assessment workflow
- `ai-service` - AI scoring (GPU-enabled if needed)
- `notification-service` - Emails, push notifications

#### 4. Global CDN + Edge Caching
- Cloud CDN for API responses (where applicable)
- Edge caching for frequently accessed data

#### 5. Dedicated Support Contract
- Google Cloud support contract
- Consider hiring DevOps/SRE

### Estimated Monthly Cost
- $1,000-3,000+/month depending on usage
- At this scale, optimize for cost efficiency

---

## Quick Reference Commands

### Check Current Resource Usage
```bash
# Cloud Run metrics
gcloud run services describe trooth-backend --region=us-east4

# Cloud SQL connections
gcloud sql operations list --instance=app-pg --limit=5

# View logs for errors
gcloud logging read 'resource.type="cloud_run_revision" AND severity>=ERROR' --limit=50
```

### Emergency Scaling (Immediate Relief)
```bash
# Quick memory bump
gcloud run services update trooth-backend \
  --region=us-east4 \
  --memory=2Gi

# Quick DB connections bump
gcloud sql instances patch app-pg \
  --database-flags=max_connections=100
```

---

## Cost Estimation Summary

| Tier | Concurrent Users | Daily Active Users | Est. Monthly Cost |
|------|------------------|--------------------|--------------------|
| Current | ~50 | ~200 | ~$30-50 |
| Tier 1 | 50-100 | 200-400 | ~$50-80 |
| Tier 2 | 100-200 | 500-1000 | ~$100-150 |
| Tier 3 | 200-500 | 1000-2500 | ~$200-350 |
| Tier 4 | 500-1000 | 2500-5000 | ~$500-800 |
| Tier 5 | 1000+ | 5000+ | ~$1000+ |

*Costs are estimates and depend on actual usage patterns, region, and Google Cloud pricing changes.*

---

## When NOT to Scale

Before scaling infrastructure, ensure you've:

1. ✅ Optimized database queries (add indexes, fix N+1 queries)
2. ✅ Implemented caching where appropriate
3. ✅ Removed unnecessary API calls from frontend
4. ✅ Compressed response payloads
5. ✅ Lazy-loaded non-critical data

Often a 2x performance improvement can be achieved through code optimization before spending more on infrastructure.
