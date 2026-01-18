#!/bin/bash
# Run load test with both apprentice and mentor tokens

set -e

cd "$(dirname "$0")/.."

echo "🔐 Getting apprentice token..."
APPRENTICE_TOKEN=$(python3 -c "
import requests
r = requests.post(
    'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=AIzaSyDTzy7Z-LaX4wC1EH3k-MR4sbH2hiIFmAE',
    json={'email':'loadtest@test.com','password':'TestPassword123!','returnSecureToken':True}
)
print(r.json()['idToken'])
")

echo "🔐 Getting mentor token..."
MENTOR_TOKEN=$(python3 -c "
import requests
r = requests.post(
    'https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=AIzaSyDTzy7Z-LaX4wC1EH3k-MR4sbH2hiIFmAE',
    json={'email':'loadtest-mentor@test.com','password':'TestPassword123!','returnSecureToken':True}
)
print(r.json()['idToken'])
")

echo ""
echo "✅ Tokens obtained!"
echo ""
echo "🚀 Starting load test..."
echo "   - Apprentice user: loadtest@test.com"
echo "   - Mentor user: loadtest-mentor@test.com"
echo "   - Target: https://trooth-backend-dev-ignpknnbva-uk.a.run.app"
echo ""

k6 run load_tests/infrastructure_test.js \
    -e AUTH_TOKEN="$APPRENTICE_TOKEN" \
    -e MENTOR_TOKEN="$MENTOR_TOKEN"
