# Google OAuth Configuration Guide

## ✅ What I Fixed

Moved allauth URLs outside `i18n_patterns` so the callback URL is:
- ✅ `http://localhost:8000/accounts/google/login/callback/` 
- ❌ NOT `http://localhost:8000/en/accounts/google/login/callback/`

## 🔧 For Local Testing (Development)

### Your current Google Console configuration is correct:
- **Authorized JavaScript origins:** `http://localhost:8000`
- **Authorized redirect URIs:** `http://localhost:8000/accounts/google/login/callback/`

### To test locally:

1. **Restart your Django server:**
   ```bash
   source venv/bin/activate
   python manage.py runserver
   ```

2. **Go to:** `http://localhost:8000/en/users/login/`

3. **Click "Sign in with Google"** - it should now work! ✅

---

## 🚀 For Production Deployment

### 1. Update Google Cloud Console

Go to [Google Cloud Console](https://console.cloud.google.com/) → OAuth Client:

**Add Production URLs:**
- **Authorized JavaScript origins:**
  - Add: `https://yourdomain.com`
  - Add: `https://www.yourdomain.com` (if using www)

- **Authorized redirect URIs:**
  - Add: `https://yourdomain.com/accounts/google/login/callback/`
  - Add: `https://www.yourdomain.com/accounts/google/login/callback/` (if using www)

**Keep the localhost URLs** for development testing.

### 2. Update Django Site in Production

Once deployed, you need to update the Site object:

**Option A - Using Django Admin:**
```
https://yourdomain.com/admin/sites/site/1/change/
```
Change domain from `localhost:8000` to `yourdomain.com`

**Option B - Using Django Shell:**
```bash
python manage.py shell
```
```python
from django.contrib.sites.models import Site
site = Site.objects.get(id=1)
site.domain = 'yourdomain.com'
site.name = 'Reserva Ya'
site.save()
```

### 3. Update Environment Variables on Production

Make sure your production server has the same `.env` variables:
```bash
GOOGLE_OAUTH_CLIENT_ID="your-client-id-here.apps.googleusercontent.com"
GOOGLE_OAUTH_CLIENT_SECRET="your-client-secret-here"
```

### 4. Production Settings Checklist

In your production environment, ensure:
- ✅ `DEBUG = False`
- ✅ `ALLOWED_HOSTS` includes your domain
- ✅ HTTPS is enabled (required by Google OAuth)
- ✅ Environment variables are loaded
- ✅ Django Site object points to production domain

---

## 🔒 Security Note

**Keep the same Client ID and Secret for both dev and prod**, or create separate OAuth clients:
- **Development Client:** `localhost:8000` URLs
- **Production Client:** `yourdomain.com` URLs

If using separate clients, update `.env` on each environment accordingly.

---

## ✅ Testing Checklist

### Local:
- [ ] Google button appears on login page
- [ ] Clicking redirects to Google login
- [ ] After Google login, redirects back to site
- [ ] User is authenticated and logged in

### Production:
- [ ] Same as local testing
- [ ] SSL/HTTPS works
- [ ] Correct domain in Site settings
- [ ] Environment variables configured

---

## 🐛 Common Issues

**"redirect_uri_mismatch"**
→ URL in Google Console must exactly match callback URL (check trailing slashes!)

**"Social application not found"**
→ Run `python manage.py setup_google_oauth` or configure in Django Admin

**"Site matching query does not exist"**
→ Update SITE_ID in settings.py or create Site object in admin
