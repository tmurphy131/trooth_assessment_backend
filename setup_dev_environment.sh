#!/bin/bash
# Script to set up T[root]H Development Environment
# Run this after app-pg-dev instance is created

set -e

PROJECT_ID="trooth-prod"
REGION="us-east4"
PROD_INSTANCE="app-pg"
DEV_INSTANCE="app-pg-dev"
PROD_DB="trooth_db"
DEV_DB="trooth_db"

echo "=== T[root]H Dev Environment Setup ==="
echo ""

# Step 1: Wait for dev instance to be ready
echo "Step 1: Checking if dev instance is ready..."
gcloud sql instances describe $DEV_INSTANCE --format="get(state)" || {
  echo "ERROR: Dev instance not found. Create it first with:"
  echo "gcloud sql instances create $DEV_INSTANCE --database-version=POSTGRES_16 --tier=db-f1-micro --region=$REGION"
  exit 1
}

# Step 2: Create database in dev instance
echo ""
echo "Step 2: Creating database '$DEV_DB' in dev instance..."
gcloud sql databases create $DEV_DB --instance=$DEV_INSTANCE 2>/dev/null || echo "Database already exists"

# Step 3: Export production database
echo ""
echo "Step 3: Exporting production database..."
EXPORT_FILE="gs://${PROJECT_ID}-backups/trooth_db_export_$(date +%Y%m%d_%H%M%S).sql"
gcloud sql export sql $PROD_INSTANCE $EXPORT_FILE \
  --database=$PROD_DB \
  --offload

echo "Export started: $EXPORT_FILE"
echo "Waiting for export to complete..."

# Wait for export operation
sleep 10
gcloud sql operations list --instance=$PROD_INSTANCE --limit=1 --filter="operationType=EXPORT" --format="value(status)"

# Step 4: Import to dev database
echo ""
echo "Step 4: Importing to dev database..."
echo "Run this command once export completes:"
echo ""
echo "gcloud sql import sql $DEV_INSTANCE $EXPORT_FILE --database=$DEV_DB"
echo ""

# Step 5: Create postgres user for dev
echo "Step 5: Setting up dev database user..."
echo "Set password for postgres user:"
echo "gcloud sql users set-password postgres --instance=$DEV_INSTANCE --password=YOUR_DEV_PASSWORD"
echo ""

# Step 6: Deploy dev backend
echo "Step 6: Deploy dev backend to Cloud Run..."
echo "Commands:"
echo ""
echo "# Build dev image"
echo "docker buildx build --platform linux/amd64 -t gcr.io/$PROJECT_ID/trooth-backend-dev:latest --push ."
echo ""
echo "# Deploy dev service"
echo "gcloud run deploy trooth-backend-dev \\"
echo "  --image=gcr.io/$PROJECT_ID/trooth-backend-dev:latest \\"
echo "  --region=$REGION \\"
echo "  --set-env-vars=ENV=development,APP_URL=https://trooth-discipleship-api-dev.onlyblv.com \\"
echo "  --set-secrets=DATABASE_URL=DATABASE_URL_DEV:latest,FIREBASE_CERT_JSON=FIREBASE_CERT_JSON:latest,SENDGRID_API_KEY=SENDGRID_API_KEY:latest,OPENAI_API_KEY=OPENAI_API_KEY:latest \\"
echo "  --allow-unauthenticated"
echo ""

echo "=== Next Steps ==="
echo "1. Wait for dev database creation to complete (check: gcloud sql instances list)"
echo "2. Create DATABASE_URL_DEV secret with connection string for dev database"
echo "3. Run export/import commands above"
echo "4. Deploy dev backend with commands above"
echo "5. Update Flutter app to point to dev backend URL for testing"
