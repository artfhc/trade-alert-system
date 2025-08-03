# Gmail Pub/Sub Setup Guide

This guide explains how to set up Gmail Pub/Sub integration for the trade alert system.

## 📋 Prerequisites

1. Google Cloud Project
2. Gmail account for receiving trade alerts
3. Python environment with required dependencies

## 🚀 Step 1: Google Cloud Setup

### Create a Google Cloud Project
```bash
# Install Google Cloud CLI
# https://cloud.google.com/sdk/docs/install

# Create project
gcloud projects create your-trade-alerts-project
gcloud config set project your-trade-alerts-project

# Enable required APIs
gcloud services enable gmail.googleapis.com
gcloud services enable pubsub.googleapis.com
```

### Create Pub/Sub Topic
```bash
# Create topic for Gmail notifications
gcloud pubsub topics create gmail-trade-alerts

# Create subscription
gcloud pubsub subscriptions create gmail-alerts-sub --topic=gmail-trade-alerts
```

## 🔑 Step 2: Gmail API Credentials

### Create Service Account (Recommended for Production)
```bash
# Create service account
gcloud iam service-accounts create gmail-trade-bot \
    --display-name="Gmail Trade Alert Bot"

# Create and download key
gcloud iam service-accounts keys create credentials.json \
    --iam-account=gmail-trade-bot@your-trade-alerts-project.iam.gserviceaccount.com
```

### Or Create OAuth2 Credentials (For Development)
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to "APIs & Services" > "Credentials"
3. Click "Create Credentials" > "OAuth 2.0 Client IDs"
4. Choose "Desktop Application"
5. Download the JSON file as `gmail_credentials.json`

## 📧 Step 3: Configure Gmail Push Notifications

### Set up Gmail Watch
```python
# Example script to set up Gmail watch
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

# Set up Gmail API client (using your credentials)
service = build('gmail', 'v1', credentials=creds)

# Configure watch request
request = {
    'labelIds': ['INBOX'],  # or specific labels for trade alerts
    'topicName': 'projects/your-trade-alerts-project/topics/gmail-trade-alerts'
}

# Start watching
result = service.users().watch(userId='me', body=request).execute()
print(f"Watch setup: {result}")
```

## 🔧 Step 4: Environment Configuration

### Update .env file
```bash
# Copy example environment file
cp tradeflow/.env.example tradeflow/.env

# Edit with your values
GOOGLE_CREDENTIALS_FILE=path/to/credentials.json
GMAIL_CREDENTIALS_FILE=path/to/gmail_credentials.json
GOOGLE_PROJECT_ID=your-trade-alerts-project
PUBSUB_TOPIC=gmail-trade-alerts
PUBSUB_SUBSCRIPTION=gmail-alerts-sub

# Gmail settings
GMAIL_SENDER_WHITELIST=alerts@tradingservice.com,notifications@broker.com
GMAIL_ALERT_KEYWORDS=trade,alert,buy,sell,position
```

## 🧪 Step 5: Testing

### Test Gmail API Connection
```python
from tradeflow.providers.gmail_pubsub import GmailPubSubProvider

# Create provider instance
provider = GmailPubSubProvider(
    credentials_file='gmail_credentials.json',
    sender_whitelist=['alerts@tradingservice.com']
)

print(f"Provider source: {provider.get_source_name()}")
```

### Test Pub/Sub Message Processing
```python
# Mock Pub/Sub message format
mock_message = {
    "message": {
        "data": "base64_encoded_gmail_notification",
        "attributes": {
            "messageId": "gmail_message_123"
        }
    }
}

# Process the message
try:
    alert = provider.parse_alert(mock_message)
    print(f"Alert parsed: {alert}")
except Exception as e:
    print(f"Error: {e}")
```

## 🌐 Step 6: Webhook Setup

### Configure FastAPI Webhook
```python
# In your FastAPI application
@app.post("/webhook/gmail")
async def gmail_webhook(request: Request):
    data = await request.json()
    
    # Process Pub/Sub message
    provider = GmailPubSubProvider()
    alert = provider.parse_alert(data)
    
    # Handle the alert (trade processing)
    # ... your trade logic here
    
    return {"status": "success"}
```

### Deploy Webhook
- Deploy to Render, Railway, or your preferred platform
- Note the webhook URL (e.g., `https://your-app.onrender.com/webhook/gmail`)

## 🔗 Step 7: Connect Pub/Sub to Webhook

### Create Push Subscription
```bash
# Create push subscription that sends to your webhook
gcloud pubsub subscriptions create gmail-webhook-sub \
    --topic=gmail-trade-alerts \
    --push-endpoint=https://your-app.onrender.com/webhook/gmail
```

## 📝 Step 8: Email Filter Setup

### Gmail Filters (Optional)
1. Go to Gmail Settings > Filters and Blocked Addresses
2. Create filter for trade alert emails:
   - From: your trade alert service
   - Subject contains: "trade alert" or similar
3. Apply label: "TradeAlerts"
4. Update Gmail watch to monitor this label specifically

## 🔍 Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify credentials file path
   - Check OAuth2 scopes
   - Refresh expired tokens

2. **Pub/Sub Not Receiving Messages**
   - Verify Gmail watch is active
   - Check topic/subscription configuration
   - Ensure proper IAM permissions

3. **Webhook Not Triggered**
   - Verify push subscription endpoint
   - Check webhook URL accessibility
   - Review application logs

### Debug Commands
```bash
# Test Pub/Sub connectivity
gcloud pubsub topics publish gmail-trade-alerts --message="test"

# Check subscriptions
gcloud pubsub subscriptions list

# Monitor logs
gcloud logging read "resource.type=gce_instance"
```

## 🔒 Security Considerations

1. **Credentials Management**
   - Store credentials securely (use environment variables)
   - Rotate credentials regularly
   - Use service accounts for production

2. **Webhook Security**
   - Implement signature verification
   - Use HTTPS only
   - Add rate limiting

3. **Email Security**
   - Whitelist trusted senders
   - Validate email content
   - Monitor for suspicious activity

## 📚 Additional Resources

- [Gmail API Documentation](https://developers.google.com/gmail/api)
- [Cloud Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [Google Cloud IAM](https://cloud.google.com/iam/docs)