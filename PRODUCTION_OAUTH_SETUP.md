# Google OAuth Production Deployment Guide

## Prerequisites
- Production domain (e.g., `yourdomain.com`)
- HTTPS/SSL enabled on production server
- Access to production server via SSH
- Access to Google Cloud Console

---

## Step 1: Update Google Cloud Console for Production

### 1.1 Add Production URLs to OAuth Client

Go to [Google Cloud Console](https://console.cloud.google.com/) → Your Project → Credentials

Click on your OAuth 2.0 Client ID (the one you created)

**Add to Authorized JavaScript origins:**
```
https://yourdomain.com
https://www.yourdomain.com
```
⚠️ Keep the localhost URLs for development

**Add to Authorized redirect URIs:**
```
https://yourdomain.com/accounts/google/login/callback/
https://www.yourdomain.com/accounts/google/login/callback/
```
⚠️ Keep the localhost redirect URI for development

Click **Save**

---

## Step 2: Configure Production Server

### 2.1 SSH into Production Server
```bash
ssh ubuntu@your-server-ip
cd /path/to/reserva-ya
```

### 2.2 Create/Update .env File on Production

```bash
nano .env
```

Add these lines (use the same credentials as development):
```bash
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID="your_google_client_id_here.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET="your_google_client_secret_here"

# Stripe Configuration (if needed)
STRIPE_PUBLIC_KEY="your_stripe_key"
STRIPE_SECRET_KEY="your_stripe_secret"
STRIPE_WEBHOOK_SECRET="your_webhook_secret"
```

Save and exit (Ctrl+O, Enter, Ctrl+X)

### 2.3 Set Proper Permissions
```bash
chmod 600 .env
chown ubuntu:ubuntu .env
```

---

## Step 3: Update Django Site Configuration

### Option A: Using Django Shell (Recommended)

```bash
source venv/bin/activate
python manage.py shell
```

Then in the Python shell:
```python
from django.contrib.sites.models import Site

# Update the site with your production domain
site = Site.objects.get(id=1)
site.domain = 'yourdomain.com'  # Replace with your actual domain
site.name = 'Reserva Ya'
site.save()

print(f"Site updated: {site.domain}")
exit()
```

### Option B: Using Django Admin (Alternative)

1. Go to: `https://yourdomain.com/admin/`
2. Login as superuser
3. Navigate to: **Sites** → **example.com**
4. Change:
   - **Domain name:** `yourdomain.com`
   - **Display name:** `Reserva Ya`
5. Click **Save**

---

## Step 4: Setup Google OAuth Social Application

### Option A: Using Management Command (Fastest)

```bash
source venv/bin/activate
python manage.py setup_google_oauth --site-domain yourdomain.com
```

This will automatically:
- Create or update the Google OAuth social application
- Associate it with your production site
- Configure the credentials from .env

### Option B: Using Django Admin (Manual)

1. Go to: `https://yourdomain.com/admin/socialaccount/socialapp/`
2. If exists, click on "Google OAuth", otherwise click "Add social application"
3. Fill in:
   - **Provider:** Google
   - **Name:** Google OAuth
   - **Client id:** `your_google_client_id_here.apps.googleusercontent.com`
   - **Secret key:** `your_google_client_secret_here`
   - **Sites:** Select `yourdomain.com` (move from Available to Chosen)
4. Click **Save**

---

## Step 5: Update Production Settings (If Needed)

Check your production settings file:

```bash
nano app/settings.py  # or app/production_settings.py
```

Ensure these are configured:

```python
# Production settings
DEBUG = False
ALLOWED_HOSTS = ['yourdomain.com', 'www.yourdomain.com']

# Site ID (should match database)
SITE_ID = 1

# Allauth is already configured, but verify these exist:
ACCOUNT_ADAPTER = 'users.adapters.CustomAccountAdapter'
SOCIALACCOUNT_ADAPTER = 'users.adapters.CustomSocialAccountAdapter'
SOCIALACCOUNT_AUTO_SIGNUP = True

# Security settings for production
SECURE_SSL_REDIRECT = True  # Force HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
```

---

## Step 6: Restart Production Server

### If using Gunicorn:
```bash
sudo systemctl restart gunicorn
# or
sudo supervisorctl restart reserva-ya
```

### If using Docker:
```bash
docker-compose restart web
```

### If using development server (not recommended for production):
```bash
pkill -f "python.*manage.py runserver"
python manage.py runserver 0.0.0.0:8000
```

---

## Step 7: Test Google OAuth on Production

1. **Open your production site:** `https://yourdomain.com/en/users/login/`

2. **Check the "Sign in with Google" button appears**

3. **Click "Sign in with Google"**
   - Should redirect to Google login
   - After authentication, should redirect back to your site
   - User should be logged in

4. **Verify user was created:**
   - Check Django Admin → Users
   - Check User Profiles
   - Check Social accounts

---

## Step 8: Verify Database Entries

```bash
source venv/bin/activate
python manage.py shell
```

```python
from django.contrib.sites.models import Site
from allauth.socialaccount.models import SocialApp

# Check site
site = Site.objects.get(id=1)
print(f"Site: {site.domain}")

# Check social app
app = SocialApp.objects.get(provider='google')
print(f"Social App: {app.name}")
print(f"Client ID: {app.client_id[:20]}...")
print(f"Sites: {list(app.sites.all())}")

exit()
```

---

## Common Production Issues & Solutions

### Issue 1: "redirect_uri_mismatch"
**Solution:** 
- Verify redirect URI in Google Console exactly matches: `https://yourdomain.com/accounts/google/login/callback/`
- Check for http vs https
- Check for trailing slash
- Wait 5-10 minutes after updating Google Console

### Issue 2: "Social application not found"
**Solution:**
```bash
python manage.py setup_google_oauth --site-domain yourdomain.com
```

### Issue 3: "Site matching query does not exist"
**Solution:**
```bash
python manage.py shell
from django.contrib.sites.models import Site
Site.objects.create(domain='yourdomain.com', name='Reserva Ya')
```

### Issue 4: Environment variables not loading
**Solution:**
```bash
# Test if .env is being read
source venv/bin/activate
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print(os.environ.get('GOOGLE_OAUTH_CLIENT_ID'))"
```

### Issue 5: HTTPS/SSL issues
**Solution:**
- Ensure SSL certificate is valid
- Verify HTTPS is working: `curl -I https://yourdomain.com`
- Check nginx/apache SSL configuration

---

## Security Checklist for Production

- [ ] `.env` file has proper permissions (600)
- [ ] `.env` is in `.gitignore`
- [ ] `DEBUG = False` in production settings
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] SSL/HTTPS enabled and working
- [ ] `SECURE_SSL_REDIRECT = True`
- [ ] `SESSION_COOKIE_SECURE = True`
- [ ] `CSRF_COOKIE_SECURE = True`
- [ ] Google OAuth credentials are production-ready
- [ ] Site domain matches actual production domain

---

## Quick Reference Commands

**Check site configuration:**
```bash
python manage.py shell -c "from django.contrib.sites.models import Site; print(Site.objects.get(id=1).domain)"
```

**Setup OAuth:**
```bash
python manage.py setup_google_oauth --site-domain yourdomain.com
```

**Test environment variables:**
```bash
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('Client ID:', os.environ.get('GOOGLE_OAUTH_CLIENT_ID', 'NOT SET'))"
```

**Restart services:**
```bash
sudo systemctl restart gunicorn nginx
```

---

## Support

If you encounter issues:
1. Check Django logs: `tail -f /var/log/gunicorn/error.log`
2. Check nginx logs: `tail -f /var/log/nginx/error.log`
3. Check Django debug mode temporarily (then disable)
4. Verify all URLs use HTTPS

Remember: Google can take 5-10 minutes to propagate OAuth configuration changes.
