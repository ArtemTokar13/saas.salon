# OpenStreetMap with Leaflet (Currently Implemented)

✅ **This is the current implementation** - No additional setup needed!

The application uses **OpenStreetMap with Leaflet** for address geocoding and map display. This is a **completely free** solution with no API keys or usage limits.

## Features

✅ **No API key required** - Works out of the box
✅ **No usage limits** - No billing or rate limits for normal use
✅ **Address Search** - Enter address and click "Find Location"
✅ **Automatic Geocoding** - Converts address to coordinates
✅ **Interactive Map** - Shows location with OpenStreetMap tiles
✅ **Draggable Marker** - Fine-tune exact position
✅ **Auto-fill City** - Extracts city from address
✅ **Free Forever** - Uses open-source OpenStreetMap data

## How to Use

1. **Edit Company Profile** - Go to your company settings
2. **Enter Address** - Type your full address in the address field
3. **Add City** (optional) - Enter city for more accurate results
4. **Click "Find Location"** - Button searches and geocodes the address
5. **View Map** - Interactive map shows the location
6. **Adjust if Needed** - Drag the marker to fine-tune position
7. **Save** - Coordinates are automatically saved

## Technical Details

The implementation uses:
- **Leaflet 1.9.4** - Lightweight open-source map library
- **OpenStreetMap Tiles** - Free map tiles from openstreetmap.org
- **Nominatim API** - Free geocoding service by OpenStreetMap

All code is already in `/templates/companies/edit_profile.html` - no additional setup needed!

## Original Implementation Code (For Reference)

The following code is already implemented in the template:

## Implementation

### Step 1: Update edit_profile.html

Replace the Google Maps section with this OpenStreetMap implementation:

```html
<!-- In the <head> or before </body> -->
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>

<script>
let map;
let marker;

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
    const addressInput = document.getElementById('id_address');
    const cityInput = document.getElementById('id_city');
    const mapLocationInput = document.getElementById('id_map_location');
    
    // Add search button next to address
    const searchBtn = document.createElement('button');
    searchBtn.type = 'button';
    searchBtn.className = 'mt-2 bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700';
    searchBtn.textContent = 'Find Location';
    searchBtn.onclick = searchAddress;
    addressInput.parentElement.appendChild(searchBtn);
    
    // Initialize map if coordinates exist
    const currentMapLocation = mapLocationInput.value;
    if (currentMapLocation && currentMapLocation.includes(',')) {
        const [lat, lng] = currentMapLocation.split(',').map(parseFloat);
        if (!isNaN(lat) && !isNaN(lng)) {
            showMapPreview(lat, lng);
        }
    }
});

async function searchAddress() {
    const addressInput = document.getElementById('id_address');
    const cityInput = document.getElementById('id_city');
    const mapLocationInput = document.getElementById('id_map_location');
    
    const address = addressInput.value.trim();
    const city = cityInput.value.trim();
    
    if (!address) {
        alert('Please enter an address');
        return;
    }
    
    // Build search query
    const query = city ? `${address}, ${city}` : address;
    
    try {
        // Use Nominatim for geocoding (free OpenStreetMap service)
        const response = await fetch(
            `https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(query)}&limit=1`,
            {
                headers: {
                    'User-Agent': 'ReservaYa Salon Booking Platform'
                }
            }
        );
        
        const data = await response.json();
        
        if (data && data.length > 0) {
            const result = data[0];
            const lat = parseFloat(result.lat);
            const lng = parseFloat(result.lon);
            
            // Update map location field
            mapLocationInput.value = `${lat},${lng}`;
            
            // Extract and update city if not already set
            if (!city && result.address) {
                if (result.address.city) {
                    cityInput.value = result.address.city;
                } else if (result.address.town) {
                    cityInput.value = result.address.town;
                } else if (result.address.village) {
                    cityInput.value = result.address.village;
                }
            }
            
            // Update address with display name if better
            if (result.display_name) {
                addressInput.value = result.display_name;
            }
            
            // Show map
            showMapPreview(lat, lng);
        } else {
            alert('Address not found. Please try a different search.');
        }
    } catch (error) {
        console.error('Geocoding error:', error);
        alert('Error searching for address. Please try again.');
    }
}

function showMapPreview(lat, lng) {
    const mapPreview = document.getElementById('map-preview');
    const mapDiv = document.getElementById('map');
    
    mapPreview.style.display = 'block';
    
    if (!map) {
        // Initialize Leaflet map
        map = L.map(mapDiv).setView([lat, lng], 15);
        
        // Add OpenStreetMap tiles
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors',
            maxZoom: 19
        }).addTo(map);
        
        // Add draggable marker
        marker = L.marker([lat, lng], {
            draggable: true
        }).addTo(map);
        
        // Update coordinates when marker is dragged
        marker.on('dragend', function(e) {
            const position = marker.getLatLng();
            document.getElementById('id_map_location').value = `${position.lat},${position.lng}`;
        });
    } else {
        // Update existing map
        map.setView([lat, lng], 15);
        marker.setLatLng([lat, lng]);
    }
}
</script>
```

### Step 2: Update the Address Field HTML

Make sure your address field looks like this:

```html
<div>
    <label class="block text-sm font-medium text-gray-700 mb-2">Address</label>
    <input type="text" id="id_address" name="address" 
           value="{{ form.address.value|default:'' }}" 
           placeholder="Enter your full address..." 
           class="w-full">
    {% if form.address.errors %}
        <p class="mt-1 text-sm text-red-600">{{ form.address.errors.0 }}</p>
    {% endif %}
</div>
```

## How It Works

1. **User enters address** in the address field
2. **Clicks "Find Location"** button
3. **Nominatim API** (free OpenStreetMap geocoding service) searches for the address
4. **Coordinates are found** and filled into the map_location field
5. **Interactive map appears** showing the location
6. **User can drag marker** to fine-tune the exact position

## Advantages

✅ **Completely Free** - No API keys, no billing, no limits
✅ **No Registration** - Works immediately
✅ **Open Source** - Uses OpenStreetMap data
✅ **Privacy Friendly** - No tracking by large corporations
✅ **Lightweight** - Leaflet is smaller than Google Maps

## Limitations

⚠️ **No Autocomplete** - User must type full address and click search
⚠️ **Rate Limited** - Nominatim has rate limits (1 request/second)
⚠️ **Less Detailed** - May not find very specific addresses in some areas

## Usage Policy

From Nominatim's usage policy:
- Maximum 1 request per second
- Provide a valid User-Agent header (already included above)
- For high-volume usage, consider running your own Nominatim instance

## For Production

If you expect high traffic, consider:

1. **Self-hosted Nominatim** - Run your own instance
2. **Commercial Nominatim providers** - Like LocationIQ (has free tier)
3. **Caching** - Cache geocoding results in your database

## Comparison: Google Maps vs OpenStreetMap

| Feature | Google Maps | OpenStreetMap |
|---------|-------------|---------------|
| **Cost** | $200/month free, then paid | Completely free |
| **API Key** | Required | Not required |
| **Autocomplete** | Yes, real-time | No (manual search) |
| **Map Quality** | Excellent | Very good |
| **Address Coverage** | Best for US/EU | Global, varies by region |
| **Setup Complexity** | Medium | Easy |
| **Best For** | Commercial apps with budget | Small businesses, MVPs |

## Recommendation

- **Use OpenStreetMap if:** You want zero cost, simple setup, or don't need autocomplete
- **Use Google Maps if:** You want best UX, real-time autocomplete, and perfect address data
