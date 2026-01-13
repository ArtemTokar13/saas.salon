# salon_flutter_app

A Flutter application for Salon SaaS booking system.

## Getting Started

### Prerequisites

- Flutter SDK (3.0.0 or higher)
- Dart SDK
- Android Studio / Xcode (for mobile development)
- VS Code with Flutter extensions (recommended)

### Installation

1. Install Flutter dependencies:
```bash
cd salon_flutter_app
flutter pub get
```

2. Update the API endpoint in `lib/config/api_config.dart`:
```dart
static const String baseUrl = 'http://your-django-backend-url';
```

### Running the App

```bash
# Run on connected device/emulator
flutter run

# Run on specific device
flutter devices
flutter run -d <device-id>

# Run in web browser
flutter run -d chrome
```

### Building the App

```bash
# Build APK for Android
flutter build apk

# Build iOS app
flutter build ios

# Build for web
flutter build web
```

## Features

- **Authentication**: Login and registration
- **Bookings Management**: Create, view, and cancel bookings
- **Profile Management**: View and edit user profile
- **Multi-language Support**: EN, ES, CA, UK
- **Responsive Design**: Works on mobile, tablet, and web

## Project Structure

```
lib/
├── config/           # App configuration (theme, API)
├── models/           # Data models
├── providers/        # State management (Provider)
├── screens/          # UI screens
│   ├── auth/         # Authentication screens
│   ├── bookings/     # Booking screens
│   └── profile/      # Profile screens
├── services/         # API services
└── main.dart         # App entry point
```

## API Integration

The app is configured to work with your Django backend. Make sure to:

1. Update `baseUrl` in `lib/config/api_config.dart`
2. Ensure your Django API endpoints match the ones defined in `api_config.dart`
3. Configure CORS in your Django backend to allow requests from the Flutter app

## Dependencies

- **provider**: State management
- **go_router**: Navigation
- **http** & **dio**: HTTP clients
- **shared_preferences**: Local storage
- **intl**: Internationalization

## Next Steps

1. Customize the theme in `lib/config/theme.dart`
2. Add your salon logo and images to `assets/`
3. Implement company and service listing screens
4. Add image picker for profile photos
5. Implement payment integration
6. Add push notifications

## License

This project is part of the Salon SaaS platform.
