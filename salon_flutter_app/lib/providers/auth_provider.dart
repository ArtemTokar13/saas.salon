import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user.dart';
import '../services/api_service.dart';

class AuthProvider with ChangeNotifier {
  User? _user;
  String? _token;
  bool _isLoading = false;
  String? _error;

  User? get user => _user;
  String? get token => _token;
  bool get isLoading => _isLoading;
  String? get error => _error;
  bool get isAuthenticated => _user != null && _token != null;

  final ApiService _apiService = ApiService();

  AuthProvider() {
    _loadUser();
  }

  Future<void> _loadUser() async {
    final prefs = await SharedPreferences.getInstance();
    _token = prefs.getString('auth_token');
    final userJson = prefs.getString('user');
    
    if (_token != null && userJson != null) {
      try {
        // Parse user from stored JSON
        // _user = User.fromJson(jsonDecode(userJson));
        notifyListeners();
      } catch (e) {
        await logout();
      }
    }
  }

  Future<bool> login(String email, String password) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await _apiService.login(email, password);
      _token = response['token'];
      _user = User.fromJson(response['user']);

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', _token!);
      // await prefs.setString('user', jsonEncode(_user!.toJson()));

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<bool> register({
    required String email,
    required String password,
    String? firstName,
    String? lastName,
    String? phone,
  }) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final response = await _apiService.register(
        email: email,
        password: password,
        firstName: firstName,
        lastName: lastName,
        phone: phone,
      );
      
      _token = response['token'];
      _user = User.fromJson(response['user']);

      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('auth_token', _token!);
      // await prefs.setString('user', jsonEncode(_user!.toJson()));

      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> logout() async {
    try {
      if (_token != null) {
        await _apiService.logout(_token!);
      }
    } catch (e) {
      // Ignore logout errors
    }

    _user = null;
    _token = null;

    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('auth_token');
    await prefs.remove('user');

    notifyListeners();
  }

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
