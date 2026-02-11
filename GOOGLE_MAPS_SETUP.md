# Google Maps API Setup for Address Autocomplete (Optional)

**Note:** The application now uses **OpenStreetMap by default** which is completely free and requires no API key. This guide is for those who prefer Google Maps' real-time autocomplete feature.

## Current Implementation: OpenStreetMap (Free)

The edit company profile page currently uses **OpenStreetMap with Leaflet** which provides:
- ✅ **Free** - No API key required
- ✅ **No usage limits**
- ✅ Address search with "Find Location" button
- ✅ Interactive map with draggable marker
- ✅ Automatic geocoding to coordinates

## Why Switch to Google Maps?

Consider Google Maps if you need:

- Type an address and get autocomplete suggestions
- Automatically fill the city field
- Get precise latitude/longitude coordinates
- Preview the location on an interactive map
- Drag the marker to fine-tune the position

## Setup Instructions

### 1. Get a Google Maps API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Enable the following APIs:
   - **Maps JavaScript API**
   - **Places API**
   - **Geocoding API** (optional, but recommended)

4. Create credentials:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "API Key"
   - Copy your API key

### 2. Secure Your API Key (Important!)

1. Click on your API key to edit it
2. Under "Application restrictions":
   - Choose "HTTP referrers (web sites)"
   - Add your domain(s):
     ```
     https://yourdomain.com/*
     http://localhost:8000/*  (for development)
     ```

3. Under "API restrictions":
   - Choose "Restrict key"
   - Select only:
     - Maps JavaScript API
     - Places API
     - Geocoding API

### 3. Configure Your Application

#### Option A: Environment Variable (Recommended for Production)

Add to your `.env` file or environment variables:
```bash
GOOGLE_MAPS_API_KEY=your_api_key_here
```

Then update `templates/companies/edit_profile.html`:
```html
<script src="https://maps.googleapis.com/maps/api/js?key={{ GOOGLE_MAPS_API_KEY }}&libraries=places&callback=initAutocomplete" async defer></script>
```

Update `app/settings.py`:
```python
GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY', '')
```

Update `app/context_processors.py` to make it available in templates:
```python
def google_maps(request):
    return {
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY
    }
```

And add to `TEMPLATES` context_processors in `settings.py`:
```python
'context_processors': [
    # ... existing processors
    'app.context_processors.google_maps',
],
```

#### Option B: Direct Replacement (Quick Setup)

Replace `YOUR_GOOGLE_MAPS_API_KEY` in `/home/ubuntu/reserva-ya/templates/companies/edit_profile.html` with your actual API key:

```html
<script src="https://maps.googleapis.com/maps/api/js?key=AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXX&libraries=places&callback=initAutocomplete" async defer></script>
```

**⚠️ Note:** This method exposes your API key in the HTML. Use Option A for production.

## Features Included

### 1. Address Autocomplete
- Start typing an address in the "Address" field
- Get real-time suggestions from Google Places
- Select from dropdown to auto-fill

### 2. Auto-fill City
- When you select an address, the city field is automatically filled
- Extracts city from Google Places data

### 3. Automatic Coordinates
- `map_location` field is automatically populated with `latitude,longitude`
- Format: `40.7128,-74.0060` (example for New York)

### 4. Interactive Map Preview
- See the selected location on a map
- Drag the marker to fine-tune the exact position
- Coordinates update automatically when marker is moved

## Pricing

Google Maps offers a **free tier**:
- **$200 free credit per month**
- Covers approximately:
  - 28,000 map loads per month
  - 40,000 autocomplete requests per month

For most small to medium businesses, this is more than sufficient.

## Troubleshooting

### Map not showing?
1. Check browser console for errors
2. Verify API key is correct
3. Ensure APIs are enabled in Google Cloud Console
4. Check domain restrictions match your URL

### Autocomplete not working?
1. Verify Places API is enabled
2. Check for JavaScript errors in console
3. Ensure the callback function `initAutocomplete` is loaded

### "RefererNotAllowedMapError"?
- Your domain is not authorized in API key restrictions
- Add your domain in Google Cloud Console > API Key settings

## Alternative: OpenStreetMap (Free)

If you prefer not to use Google Maps, you can use OpenStreetMap with Nominatim for geocoding (completely free):

See `OPENSTREETMAP_SETUP.md` for instructions on implementing a free alternative.
