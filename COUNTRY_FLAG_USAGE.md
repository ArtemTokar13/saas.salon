# Country Code & Flag Implementation Guide

## What Was Added

### 1. **Model Updates** (`bookings/models.py`)
- Added `COUNTRY_CHOICES` with 50+ countries and flag emojis
- Updated `Customer.country_code` field to use these choices

### 2. **Form Updates** (`bookings/forms.py`)
- Added `customer_country_code` field to `BookingForm`
- Automatically saves country code when creating/updating customers

### 3. **Template Filters** (`bookings/templatetags/booking_extras.py`)
Two new filters available:
- `country_flag`: Returns just the flag emoji
- `country_name`: Returns flag + country name

## Usage in Templates

### Add to Template Header
```django
{% load booking_extras %}
```

### Display Country Flag Only
```django
{{ customer.country_code|country_flag }}
```

### Display Flag + Country Name
```django
{{ customer.country_code|country_name }}
```

### Example: Customer Information Display
```html
{% load booking_extras %}

<div class="customer-info">
    <h3>{{ customer.name }}</h3>
    <p>Country: {{ customer.country_code|country_name }}</p>
    <p>Phone: {{ customer.phone }}</p>
    <p>Email: {{ customer.email }}</p>
</div>
```

### Example: Booking List with Flags
```html
{% load booking_extras %}

<table>
    <thead>
        <tr>
            <th>Customer</th>
            <th>Country</th>
            <th>Phone</th>
        </tr>
    </thead>
    <tbody>
        {% for booking in bookings %}
        <tr>
            <td>{{ booking.customer.name }}</td>
            <td>{{ booking.customer.country_code|country_flag }} {{ booking.customer.country_code|country_name }}</td>
            <td>{{ booking.customer.phone }}</td>
        </tr>
        {% endfor %}
    </tbody>
</table>
```

## Available Country Codes

The form now includes country selections with flag emojis:
- 🇺🇸 United States (US)
- 🇬🇧 United Kingdom (GB)
- 🇨🇦 Canada (CA)
- 🇦🇺 Australia (AU)
- And 45+ more countries...

## Database Migration

After implementing this, run:
```bash
python manage.py makemigrations
python manage.py migrate
```

This will update the `customer_code` field in the database to include the new choices.
