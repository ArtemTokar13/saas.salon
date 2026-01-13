import 'package:flutter/material.dart';
import '../models/booking.dart';
import '../models/company.dart';
import '../services/api_service.dart';

class BookingProvider with ChangeNotifier {
  List<Booking> _bookings = [];
  List<Booking> _companyBookings = [];
  List<Staff> _companyStaff = [];
  Booking? _currentBooking;
  bool _isLoading = false;
  String? _error;

  List<Booking> get bookings => _bookings;
  List<Booking> get companyBookings => _companyBookings;
  List<Staff> get companyStaff => _companyStaff;
  Booking? get currentBooking => _currentBooking;
  bool get isLoading => _isLoading;
  String? get error => _error;

  final ApiService _apiService = ApiService();

  // Fetch customer's own bookings
  Future<void> fetchBookings(String token) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _bookings = await _apiService.getBookings(token);
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  // Fetch company's bookings (for salon owners/staff)
  Future<void> fetchCompanyBookings(String token, String companyId) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _companyBookings = await _apiService.getCompanyBookings(token, companyId);
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  // Fetch company staff members
  Future<void> fetchCompanyStaff(String token, String companyId) async {
    try {
      _companyStaff = await _apiService.getCompanyStaff(token, companyId);
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      notifyListeners();
    }
  }

  // Get bookings for a specific date
  List<Booking> getBookingsForDate(DateTime date) {
    return _companyBookings.where((booking) {
      return booking.bookingDate.year == date.year &&
          booking.bookingDate.month == date.month &&
          booking.bookingDate.day == date.day;
    }).toList();
  }

  // Get bookings for a specific staff member on a date
  List<Booking> getStaffBookingsForDate(String staffId, DateTime date) {
    return getBookingsForDate(date).where((booking) {
      return booking.staffId == staffId;
    }).toList();
  }

  Future<void> fetchBookingById(String token, String id) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      _currentBooking = await _apiService.getBookingById(token, id);
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _error = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<bool> createBooking(
      String token, Map<String, dynamic> bookingData) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      final booking = await _apiService.createBooking(token, bookingData);
      _bookings.insert(0, booking);
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

  Future<bool> cancelBooking(String token, String id) async {
    _isLoading = true;
    _error = null;
    notifyListeners();

    try {
      await _apiService.cancelBooking(token, id);
      _bookings.removeWhere((b) => b.id == id);
      if (_currentBooking?.id == id) {
        _currentBooking = null;
      }
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

  void clearError() {
    _error = null;
    notifyListeners();
  }
}
