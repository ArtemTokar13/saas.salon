# Flutter App Testing Guide

## Current Status
✅ Flutter app created successfully
✅ Dependencies installed
✅ Code structure complete

## Testing Options

### Option 1: Web Browser (Recommended - Easiest)

1. **Install Chrome/Chromium** (if not available):
```bash
# For Rocky Linux/RHEL
sudo dnf install chromium
```

2. **Run the app**:
```bash
cd /home/artem/DEV/cd/saas.salon/salon_flutter_app
~/flutter/bin/flutter run -d chrome
```

### Option 2: Linux Desktop

Requires CMake and other dependencies:

```bash
# Install dependencies
sudo dnf install cmake ninja-build gtk3-devel

# Run the app
cd /home/artem/DEV/cd/saas.salon/salon_flutter_app
~/flutter/bin/flutter run -d linux
```

### Option 3: Android Emulator

1. **Install Android Studio**
2. **Set up an Android emulator**
3. **Run**:
```bash
~/flutter/bin/flutter run
```

### Option 4: Connect Physical Device

**For Android:**
1. Enable USB debugging on your Android phone
2. Connect via USB
3. Run: `~/flutter/bin/flutter devices`
4. Run: `~/flutter/bin/flutter run`

**For iOS (requires macOS):**
1. Connect iPhone/iPad
2. Run the app through Xcode

## Quick Test Without Running

To verify the code compiles without errors:

```bash
cd /home/artem/DEV/cd/saas.salon/salon_flutter_app
~/flutter/bin/flutter analyze
```

## Permanent PATH Setup

To avoid typing ~/flutter/bin/ every time, add Flutter to your PATH:

```bash
# Add to ~/.bashrc
echo 'export PATH="$HOME/flutter/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Then you can just use:
flutter run
```

## Features Implemented

✅ **Authentication System**
  - Login screen
  - Registration screen
  - JWT token management

✅ **Booking Management**
  - List all bookings
  - View booking details
  - Create new bookings
  - Cancel bookings

✅ **User Profile**
  - View profile
  - Logout functionality

✅ **Navigation**
  - Bottom navigation
  - Deep linking support
  - Authentication guards

✅ **Theming**
  - Light & dark mode
  - Material Design 3
  - Custom color scheme

✅ **Localization**
  - Multi-language support (EN, ES, CA, UK)

## Next Steps to Connect to Django

1. **Update API URL** in `lib/config/api_config.dart`:
```dart
static const String baseUrl = 'http://YOUR_DJANGO_SERVER:8000';
```

2. **Ensure Django CORS is configured**:
```python
# In Django settings.py
INSTALLED_APPS = [
    ...
    'corsheaders',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    ...
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:8080",  # Flutter web
    "http://localhost:3000",  # If using different port
]
```

3. **Match API endpoints** - The Flutter app expects these endpoints:
   - POST `/api/auth/login/`
   - POST `/api/auth/register/`
   - POST `/api/auth/logout/`
   - GET `/api/bookings/`
   - POST `/api/bookings/`
   - GET `/api/bookings/{id}/`
   - DELETE `/api/bookings/{id}/`
   - GET `/api/companies/`
   - GET `/api/companies/{id}/services/`

## Troubleshooting

### "Dart compiler exited unexpectedly"
- This can happen on systems with limited resources
- Try Linux desktop build instead of web
- Or use a physical device/emulator

### "CMake is required"
```bash
sudo dnf install cmake ninja-build gtk3-devel
```

### "Chrome/Chromium not found"
```bash
sudo dnf install chromium
```

## File Structure

```
salon_flutter_app/
├── lib/
│   ├── config/              # Configuration
│   │   ├── api_config.dart  # API endpoints ← UPDATE THIS
│   │   └── theme.dart       # App theming
│   ├── models/              # Data models
│   ├── providers/           # State management
│   ├── screens/             # UI screens
│   ├── services/            # API services
│   └── main.dart            # Entry point
├── assets/                  # Images, icons
└── pubspec.yaml             # Dependencies
```

## Support

For Flutter documentation: https://docs.flutter.dev/
For Flutter API docs: https://api.flutter.dev/
