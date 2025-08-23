# Email Configuration Setup Guide

## Issue Identified
Your SendGrid email integration is not working because:

1. ❌ **SendGrid API Key**: Currently set to placeholder value `your_sendgrid_key`
2. ✅ **Jinja2**: Now installed and available for rich email templates

## 🔧 Fix Steps

### Step 1: Get Your SendGrid API Key

1. **Login to SendGrid**:
   - Go to https://sendgrid.com/
   - Sign in to your account (or create one if needed)

2. **Create API Key**:
   - Navigate to Settings → API Keys
   - Click "Create API Key"
   - Choose "Restricted Access" 
   - Grant permissions for "Mail Send" (Full Access)
   - Name it "Trooth Assessment App"
   - Copy the generated key (starts with `SG.`)

### Step 2: Update Environment Variables

1. **Edit `.env` file**:
   ```bash
   cd "/Users/tmoney/Documents/ONLY BLV/trooth_backend"
   nano .env
   ```

2. **Replace the placeholder**:
   ```properties
   # BEFORE (current):
   SENDGRID_API_KEY=your_sendgrid_key
   
   # AFTER (your real key):
   SENDGRID_API_KEY=SG.your_actual_sendgrid_api_key_here
   ```

### Step 3: Verify Domain (Important!)

1. **In SendGrid Console**:
   - Go to Settings → Sender Authentication
   - Set up Domain Authentication for your domain
   - OR use Single Sender Verification for testing

2. **Update FROM address** (if needed):
   ```properties
   EMAIL_FROM_ADDRESS=noreply@yourdomain.com
   ```

### Step 4: Test the Configuration

After updating your API key, test with:

```bash
cd "/Users/tmoney/Documents/ONLY BLV/trooth_backend"
python3 -c "
from app.services.email import send_invitation_email
result = send_invitation_email(
    to_email='your-test-email@example.com',
    apprentice_name='Test User', 
    token='test-123',
    mentor_name='Your Name'
)
print(f'Email sent: {result}')
"
```

## 🎯 Current Status

✅ **Jinja2**: Installed and ready for rich HTML emails  
✅ **Email Templates**: Available in `app/templates/email/`  
✅ **SendGrid Integration**: Code is properly implemented  
❌ **API Key**: Needs real SendGrid API key  

## 📧 What Happens After Fix

Once configured, your apprentice invitations will:
- ✅ Send automatically when mentors invite apprentices
- ✅ Include rich HTML formatting
- ✅ Have proper branding and styling
- ✅ Include working invitation links
- ✅ Show in SendGrid activity logs

## 🔍 Troubleshooting

If emails still don't send after configuration:

1. **Check SendGrid Activity**:
   - Login to SendGrid
   - Go to Activity → Email Activity
   - Look for your sent emails and any errors

2. **Verify API Key Permissions**:
   - Ensure "Mail Send" permission is enabled
   - Try regenerating the API key if needed

3. **Check Domain Authentication**:
   - Unverified domains may have sending restrictions
   - Use Single Sender Verification for testing

4. **Review Application Logs**:
   ```bash
   tail -f /Users/tmoney/Documents/ONLY\ BLV/trooth_backend/logs/app.log
   ```

## ⚡ Quick Test Command

After setting up your API key:

```bash
# Test email configuration
python3 -c "
import os
from dotenv import load_dotenv
load_dotenv()
print('SENDGRID_API_KEY configured:', not os.getenv('SENDGRID_API_KEY', '').startswith('your_'))
from app.services.email import get_sendgrid_client
print('SendGrid client ready:', get_sendgrid_client() is not None)
"
```
