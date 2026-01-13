import 'dart:convert';
import 'package:http/http.dart' as http;
import '../config/api_config.dart';
import '../models/booking.dart';
import '../models/company.dart';

class ApiService {
  // Auth endpoints
  Future<Map<String, dynamic>> login(String email, String password) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.loginEndpoint}'),
      headers: ApiConfig.headers(),
      body: jsonEncode({
        'email': email,
        'password': password,
      }),
    );

    if (response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to login: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> register({
    required String email,
    required String password,
    String? firstName,
    String? lastName,
    String? phone,
  }) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.registerEndpoint}'),
      headers: ApiConfig.headers(),
      body: jsonEncode({
        'email': email,
        'password': password,
        'first_name': firstName,
        'last_name': lastName,
        'phone': phone,
      }),
    );

    if (response.statusCode == 201 || response.statusCode == 200) {
      return jsonDecode(response.body);
    } else {
      throw Exception('Failed to register: ${response.body}');
    }
  }

  Future<void> logout(String token) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.logoutEndpoint}'),
      headers: ApiConfig.headers(token: token),
    );

    if (response.statusCode != 200 && response.statusCode != 204) {
      throw Exception('Failed to logout: ${response.body}');
    }
  }

  // Booking endpoints
  Future<List<Booking>> getBookings(String token) async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.bookingsEndpoint}'),
      headers: ApiConfig.headers(token: token),
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => Booking.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load bookings: ${response.body}');
    }
  }

  Future<Booking> getBookingById(String token, String id) async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.bookingDetailEndpoint(id)}'),
      headers: ApiConfig.headers(token: token),
    );

    if (response.statusCode == 200) {
      return Booking.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to load booking: ${response.body}');
    }
  }

  Future<Booking> createBooking(
      String token, Map<String, dynamic> bookingData) async {
    final response = await http.post(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.bookingsEndpoint}'),
      headers: ApiConfig.headers(token: token),
      body: jsonEncode(bookingData),
    );

    if (response.statusCode == 201 || response.statusCode == 200) {
      return Booking.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to create booking: ${response.body}');
    }
  }

  Future<void> cancelBooking(String token, String id) async {
    final response = await http.delete(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.bookingDetailEndpoint(id)}'),
      headers: ApiConfig.headers(token: token),
    );

    if (response.statusCode != 200 && response.statusCode != 204) {
      throw Exception('Failed to cancel booking: ${response.body}');
    }
  }

  // Company endpoints
  Future<List<Company>> getCompanies(String token) async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.companiesEndpoint}'),
      headers: ApiConfig.headers(token: token),
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => Company.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load companies: ${response.body}');
    }
  }

  Future<Company> getCompanyById(String token, String id) async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}${ApiConfig.companyDetailEndpoint(id)}'),
      headers: ApiConfig.headers(token: token),
    );

    if (response.statusCode == 200) {
      return Company.fromJson(jsonDecode(response.body));
    } else {
      throw Exception('Failed to load company: ${response.body}');
    }
  }

  Future<List<Service>> getCompanyServices(
      String token, String companyId) async {
    final response = await http.get(
      Uri.parse(
          '${ApiConfig.baseUrl}${ApiConfig.companyServicesEndpoint(companyId)}'),
      headers: ApiConfig.headers(token: token),
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => Service.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load services: ${response.body}');
    }
  }

  // Company bookings - for salon owners/staff
  Future<List<Booking>> getCompanyBookings(
      String token, String companyId) async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/api/companies/$companyId/bookings/'),
      headers: ApiConfig.headers(token: token),
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => Booking.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load company bookings: ${response.body}');
    }
  }

  // Get company staff members
  Future<List<Staff>> getCompanyStaff(String token, String companyId) async {
    final response = await http.get(
      Uri.parse('${ApiConfig.baseUrl}/api/companies/$companyId/staff/'),
      headers: ApiConfig.headers(token: token),
    );

    if (response.statusCode == 200) {
      final List<dynamic> data = jsonDecode(response.body);
      return data.map((json) => Staff.fromJson(json)).toList();
    } else {
      throw Exception('Failed to load staff: ${response.body}');
    }
  }
}
