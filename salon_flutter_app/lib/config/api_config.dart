class ApiConfig {
  // Update this with your Django backend URL
  static const String baseUrl = 'http://localhost:8000';
  
  // API endpoints
  static const String apiPrefix = '/api';
  
  // Auth endpoints
  static const String loginEndpoint = '$apiPrefix/auth/login/';
  static const String registerEndpoint = '$apiPrefix/auth/register/';
  static const String logoutEndpoint = '$apiPrefix/auth/logout/';
  static const String userEndpoint = '$apiPrefix/auth/user/';
  
  // Booking endpoints
  static const String bookingsEndpoint = '$apiPrefix/bookings/';
  static String bookingDetailEndpoint(String id) => '$apiPrefix/bookings/$id/';

  // Calendar endpoints
  static const String calendarEndpoint = '$apiPrefix/calendar/';
  
  // Company endpoints
  static const String companiesEndpoint = '$apiPrefix/companies/';
  static String companyDetailEndpoint(String id) => '$apiPrefix/companies/$id/';
  static String companyServicesEndpoint(String id) => '$apiPrefix/companies/$id/services/';
  static String companyStaffEndpoint(String id) => '$apiPrefix/companies/$id/staff/';
  
  // Service endpoints
  static const String servicesEndpoint = '$apiPrefix/services/';
  
  // Headers
  static Map<String, String> headers({String? token}) {
    final Map<String, String> defaultHeaders = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    
    if (token != null) {
      defaultHeaders['Authorization'] = 'Bearer $token';
    }
    
    return defaultHeaders;
  }
}
