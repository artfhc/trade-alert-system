# 🚀 Render Deployment Guide

This guide explains how to deploy your Trade Alert Webhook Server to Render.

## 📋 Prerequisites

1. A [Render account](https://render.com) (free tier works)
2. Your project pushed to GitHub/GitLab
3. Gmail credentials and Google Cloud project set up

## 🔧 Step 1: Prepare Your Repository

Make sure these files are in your project root:
- ✅ `requirements.txt` - Python dependencies
- ✅ `render.yaml` - Render service configuration  
- ✅ `Procfile` - Process definition
- ✅ `run_webhook_server.py` - Server startup script

## 🌐 Step 2: Deploy to Render

### Option A: Deploy via Render Dashboard

1. **Go to [Render Dashboard](https://dashboard.render.com/)**

2. **Click "New" → "Web Service"**

3. **Connect Your Repository:**
   - Choose "Build and deploy from a Git repository"
   - Connect your GitHub/GitLab account
   - Select your trade alert project repository

4. **Configure Service:**
   - **Name**: `trade-alert-webhook`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python run_webhook_server.py`
   - **Plan**: `Free` (or upgrade as needed)

### Option B: Deploy via render.yaml (Infrastructure as Code)

1. **Push render.yaml to your repository**
2. **In Render Dashboard, click "New" → "Blueprint"**
3. **Connect repository and Render will auto-deploy**

## 🔐 Step 3: Configure Environment Variables

In your Render service settings, add these environment variables:

### Required Variables:
```
ENVIRONMENT=production
DEBUG=false
HOST=0.0.0.0
PORT=10000
GOOGLE_PROJECT_ID=gmail-trade-alert-system
PUBSUB_TOPIC=gmail-trade-alerts
PUBSUB_SUBSCRIPTION=gmail-alerts-sub
```

### Gmail Configuration:
```
GMAIL_SENDER_WHITELIST=alerts@tradingservice.com,notifications@broker.com
GMAIL_ALERT_KEYWORDS=trade,alert,buy,sell,position
```

### Credentials (Upload as Files):
- Upload `gmail_credentials.json` as `GMAIL_CREDENTIALS_FILE`
- Upload `credentials.json` as `GOOGLE_CREDENTIALS_FILE`

**Important**: For credentials files, you have two options:

#### Option 1: Environment Variables (Recommended)
Convert your JSON files to base64 and store as env vars:
```bash
# Convert files to base64
base64 -i gmail_credentials.json

# In Render, create env vars:
GMAIL_CREDENTIALS_JSON=<base64_string>
GOOGLE_CREDENTIALS_JSON=<base64_string>
```

Then modify your server to decode these at runtime.

#### Option 2: Store in Repository (Less Secure)
Add credential files to your repository (NOT recommended for production).

## 🔗 Step 4: Get Your Webhook URL

After deployment, Render will provide a URL like:
```
https://trade-alert-webhook-abc123.onrender.com
```

Your webhook endpoint will be:
```
https://trade-alert-webhook-abc123.onrender.com/webhook/gmail
```

## ✅ Step 5: Test Your Deployment

Test the endpoints:

```bash
# Health check
curl https://your-app.onrender.com/health

# System status
curl https://your-app.onrender.com/status

# Manual test
curl -X POST https://your-app.onrender.com/manual-trade \
  -H "Content-Type: application/json" \
  -d '{"data": "test message"}'
```

## 📡 Step 6: Connect Pub/Sub to Your Webhook

Now create a push subscription that sends to your deployed webhook:

```bash
gcloud pubsub subscriptions create gmail-webhook-sub \
    --topic=gmail-trade-alerts \
    --push-endpoint=https://your-app.onrender.com/webhook/gmail
```

## 🔍 Step 7: Monitor Your Deployment

### View Logs
- Go to your Render service dashboard
- Click on "Logs" tab to see real-time logs
- Monitor for incoming Gmail notifications

### Service Health
- Check `/health` endpoint regularly
- Monitor `/status` for service status
- Render provides uptime monitoring

## 🚨 Troubleshooting

### Common Issues:

1. **Build Failures**
   - Check `requirements.txt` has correct dependencies
   - Verify Python version compatibility

2. **Environment Variable Issues**
   - Double-check all required env vars are set
   - Verify credential files are properly uploaded

3. **Port Issues**
   - Render expects your app to bind to `$PORT` env var
   - Our server uses `PORT` from config (should be 10000)

4. **Gmail API Errors**
   - Verify Gmail credentials are valid
   - Check that Gmail API is enabled in Google Cloud
   - Ensure OAuth2 consent screen is configured

5. **Pub/Sub Connection Issues**
   - Verify webhook URL is accessible publicly
   - Check IAM permissions for Pub/Sub publishing
   - Test webhook endpoint manually first

### Debug Commands:
```bash
# Test Pub/Sub publishing
gcloud pubsub topics publish gmail-trade-alerts --message="test"

# Check webhook accessibility
curl -X POST https://your-app.onrender.com/webhook/gmail \
  -H "Content-Type: application/json" \
  -d '{"message": {"data": "dGVzdA==", "messageId": "test123"}}'
```

## 🔒 Security Best Practices

1. **Never commit credentials to repository**
2. **Use environment variables for sensitive data**
3. **Enable HTTPS only (Render provides this automatically)**
4. **Implement webhook signature verification for production**
5. **Set up monitoring and alerting**

## 📈 Scaling Considerations

- **Free Tier**: Sleeps after 15 minutes of inactivity
- **Paid Plans**: Always-on, better performance
- **Auto-scaling**: Render handles this automatically
- **Database**: Consider adding persistent storage for trade logs

## 🎉 Success!

Once deployed, your webhook will:
- ✅ Receive Gmail Pub/Sub notifications
- ✅ Process trade alerts automatically  
- ✅ Log all activities
- ✅ Be accessible 24/7 (paid plans)

Your trade alert system is now live! 🚀