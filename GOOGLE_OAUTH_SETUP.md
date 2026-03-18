# Google OAuth Setup Guide

This guide will help you set up Google OAuth authentication for your Django application.

## Step 1: Create Google OAuth Credentials

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the Google+ API:
   - Go to "APIs & Services" > "Library"
   - Search for "Google+ API" 
   - Click "Enable"

4. Create OAuth 2.0 credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - If prompted, configure the OAuth consent screen first:
     - Choose "External" user type (unless you're using Google Workspace)
     - Fill in the app name, user support email, and developer contact information
     - Add scopes: `../auth/userinfo.email` and `../auth/userinfo.profile`
     - Add test users if needed
   
5. Configure OAuth client ID:
   - Application type: "Web application"
   - Name: Your app name (e.g., "Reserva Ya")
   - Authorized JavaScript origins:
     - `http://localhost:8000` (for development)
     - Your production domain (e.g., `https://yourdomain.com`)
   - Authorized redirect URIs:
     - `http://localhost:8000/accounts/google/login/callback/` (for development)
     - `https://yourdomain.com/accounts/google/login/callback/` (for production)
   
6. Click "Create" and copy your:
   - **Client ID**
   - **Client Secret**

## Step 2: Configure Environment Variables

Create a `.env` file in your project root (or add to existing one):

```bash
# Google OAuth Configuration
GOOGLE_OAUTH_CLIENT_ID=your_client_id_here.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=your_client_secret_here
```

## Step 3: Update Django Settings to Load from .env

If you don't already have python-dotenv configured, add to your `settings.py`:

```python
from dotenv import load_dotenv
load_dotenv()
```

The settings have already been configured to read from environment variables:
- `GOOGLE_OAUTH_CLIENT_ID` 
- `GOOGLE_OAUTH_CLIENT_SECRET`

## Step 4: Configure Social Application in Django Admin

1. Start your Django development server:
   ```bash
   source venv/bin/activate
   python manage.py runserver
   ```

2. Go to Django Admin: `http://localhost:8000/admin/`

3. Navigate to "Sites" and verify that your site exists:
   - Domain name: `localhost:8000` (for development) or your production domain
   - Display name: Your site name
   - **Note the Site ID** (usually 1)

4. Navigate to "Social applications" > "Add social application"
   - Provider: **Google**
   - Name: **Google OAuth**
   - Client id: Paste your Google Client ID
   - Secret key: Paste your Google Client Secret
   - Sites: Select your site (move it from Available to Chosen)
   - Click "Save"

## Step 5: Test the Integration

1. Make sure your server is running
2. Go to the login page: `http://localhost:8000/users/login/`
3. You should see a "Sign in with Google" button
4. Click it to test the OAuth flow

## Troubleshooting

### "redirect_uri_mismatch" Error
- Verify that the redirect URI in Google Console exactly matches: `http://localhost:8000/accounts/google/login/callback/`
- Make sure there are no trailing slashes mismatch
- Check that the domain matches exactly (localhost vs 127.0.0.1)

### "Invalid client" Error
- Double-check your Client ID and Client Secret in Django Admin
- Make sure you're using the correct credentials for the environment (dev vs production)

### Social Application Not Found
- Verify that SITE_ID in settings.py matches the Site ID in Django Admin
- Make sure the Social Application is associated with the correct site

### User Profile Fields
After successful Google OAuth login, you may want to customize what happens:
- User email is automatically captured
- You can access additional info from `socialaccount.extra_data`
- Customize signup flow in allauth settings if needed

## Production Deployment

When deploying to production:

1. Update Google OAuth credentials with production domain:
   - Add production domain to Authorized JavaScript origins
   - Add production callback URL to Authorized redirect URIs

2. Update Django Site in admin:
   - Change domain from `localhost:8000` to your production domain

3. Update environment variables on production server

4. Make sure `DEBUG = False` in production settings

## Additional Resources

- [Django Allauth Documentation](https://django-allauth.readthedocs.io/)
- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
