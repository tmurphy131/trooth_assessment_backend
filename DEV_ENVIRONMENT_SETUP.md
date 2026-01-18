# T[root]H Development Environment Setup Guide

## Overview
Setting up isolated dev environment to test changes without affecting production.

- **Production DB**: `app-pg` (trooth-prod:us-east4:app-pg)  
- **Dev DB**: `app-pg-dev` with database `trooth_db` (trooth-prod:us-east4:app-pg-dev) - Creating...
- **Production Backend**: `trooth-backend` → https://trooth-discipleship-api.onlyblv.com
- **Dev Backend**: `trooth-backend-dev` → https://trooth-discipleship-api-dev.onlyblv.com (to be created)

---

## Step 1: Wait for Dev Database Creation ✅

```bash
# Check status (should show RUNNABLE when ready)
gcloud sql instances list --format="table(name,state,region)"
```

**Status**: Currently PENDING_CREATE (takes 5-10 minutes)

---

## Step 2: Create Dev Database & Set Password

```bash
# Create database (same name as prod for parity)
gcloud sql databases create trooth_db --instance=app-pg-dev

# Set postgres password (choose a secure password)
gcloud sql users set-password postgres \
  --instance=app-pg-dev \
  --password=YOUR_SECURE_DEV_PASSWORD
```

---

## Step 3: Export Production Data

First, create a GCS bucket for backups if it doesn't exist:

```bash
# Create bucket (if needed)
gsutil mb -l us-east4 gs://trooth-prod-backups

# Export prod database
gcloud sql export sql app-pg gs://trooth-prod-backups/trooth_db_export_$(date +%Y%m%d_%H%M%S).sql \
  --database=trooth_db \
  --offload
```

**Note**: Export can take 5-15 minutes depending on database size. You can check progress:

```bash
gcloud sql operations list --instance=app-pg --limit=5
```

---

## Step 4: Import to Dev Database

```bash
# Replace EXPORT_FILE with the actual file from step 3
EXPORT_FILE="gs://trooth-prod-backups/trooth_db_export_YYYYMMDD_HHMMSS.sql"

gcloud sql import sql app-pg-dev $EXPORT_FILE \
  --database=trooth_db_dev
```

---

## Step 5: Create Dev Database Connection Secret

Get the connection name:

```bash
gcloud sql instances describe app-pg-dev --format="get(connectionName)"
# Output: trooth-prod:us-east4:app-pg-dev
```

Create DATABASE_URL_DEV secret:

```bash
# Format: postgresql://user:password@/database?host=/cloudsql/CONNECTION_NAME
echo "postgresql://postgres:YOUR_SECURE_DEV_PASSWORD@/trooth_db?host=/cloudsql/trooth-prod:us-east4:app-pg-dev" | \
  gcloud secrets create DATABASE_URL_DEV --data-file=-

# Or update if it exists
echo "postgresql://postgres:YOUR_SECURE_DEV_PASSWORD@/trooth_db?host=/cloudsql/trooth-prod:us-east4:app-pg-dev" | \
  gcloud secrets versions add DATABASE_URL_DEV --data-file=-
```

---

## Step 6: Build & Deploy Dev Backend

```bash
cd /Users/tmoney/Documents/ONLY\ BLV/trooth_assessment_backend

# Build dev image
docker buildx build --platform linux/amd64 \
  -t gcr.io/trooth-prod/trooth-backend-dev:latest \
  --push .

# Deploy dev service
gcloud run deploy trooth-backend-dev \
  --image=gcr.io/trooth-prod/trooth-backend-dev:latest \
  --region=us-east4 \
  --set-env-vars=ENV=development,APP_URL=https://trooth-discipleship-api-dev.onlyblv.com \
  --set-secrets=DATABASE_URL=DATABASE_URL_DEV:latest,FIREBASE_CERT_JSON=FIREBASE_CERT_JSON:latest,SENDGRID_API_KEY=SENDGRID_API_KEY:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest \
  --allow-unauthenticated \
  --add-cloudsql-instances=trooth-prod:us-east4:app-pg-dev
```

Get the deployed URL:

```bash
gcloud run services describe trooth-backend-dev --region=us-east4 --format="value(status.url)"
```

---

## Step 7: Update Flutter App for Dev Testing

Create a dev configuration in the Flutter app:

**Option A: Environment Variable (Recommended)**

```dart
// lib/config/env_config.dart
class EnvConfig {
  static const String environment = String.fromEnvironment('ENV', defaultValue: 'production');
  
  static String get apiBaseUrl {
    switch (environment) {
      case 'dev':
        return 'https://trooth-discipleship-api-dev.onlyblv.com';
      case 'production':
      default:
        return 'https://trooth-discipleship-api.onlyblv.com';
    }
  }
}

// Update ApiService to use EnvConfig.apiBaseUrl
```

Run with dev config:
```bash
flutter run --dart-define=ENV=dev
```

**Option B: Simple Toggle (Quick Testing)**

Edit `lib/services/api_service.dart`:

```dart
class ApiService {
  // Toggle this for dev testing
  static const bool USE_DEV = true;  // Set to true for dev, false for prod
  
  static const String _prodBase = 'https://trooth-discipleship-api.onlyblv.com';
  static const String _devBase = 'https://ACTUAL_DEV_URL_FROM_STEP_6.run.app';
  
  static final String _base = USE_DEV ? _devBase : _prodBase;
  // ... rest of code
}
```

---

## Step 8: Run Database Migrations on Dev

```bash
# SSH into Cloud Run instance or run locally with dev DATABASE_URL
export DATABASE_URL="postgresql://postgres:YOUR_SECURE_DEV_PASSWORD@/trooth_db?host=/cloudsql/trooth-prod:us-east4:app-pg-dev"

# Run migrations
cd /Users/tmoney/Documents/ONLY\ BLV/trooth_assessment_backend
source venv/bin/activate  # If using venv
alembic upgrade head
```

---

## Verification Checklist

- [ ] Dev database instance is RUNNABLE
- [ ] Dev database `trooth_db` created
- [ ] Production data exported and imported to dev
- [ ] DATABASE_URL_DEV secret created
- [ ] Dev backend deployed to Cloud Run
- [ ] Flutter app configured to use dev backend
- [ ] Test API call: `curl https://YOUR_DEV_URL/health`

---

## Cost Management

Dev instance uses `db-f1-micro` tier (~$7/month) vs prod's custom tier.

To stop dev instance when not in use:
```bash
gcloud sql instances patch app-pg-dev --activation-policy=NEVER
```

To restart:
```bash
gcloud sql instances patch app-pg-dev --activation-policy=ALWAYS
```

---

## Troubleshooting

### Cloud SQL connection issues
```bash
# Check Cloud SQL proxy is enabled
gcloud run services describe trooth-backend-dev --region=us-east4 --format="get(spec.template.spec.containers[0].resources.cloudsqlInstances)"
```

### Database connection test
```bash
gcloud sql connect app-pg-dev --user=postgres --database=trooth_db
```

### View logs
```bash
gcloud run services logs read trooth-backend-dev --region=us-east4 --limit=50
```
