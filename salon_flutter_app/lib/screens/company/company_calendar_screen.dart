import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import '../../providers/auth_provider.dart';
import '../../providers/booking_provider.dart';
import '../../models/booking.dart';
import '../../models/company.dart';

class CompanyCalendarScreen extends StatefulWidget {
  const CompanyCalendarScreen({super.key});

  @override
  State<CompanyCalendarScreen> createState() => _CompanyCalendarScreenState();
}

class _CompanyCalendarScreenState extends State<CompanyCalendarScreen> {
  DateTime _selectedDate = DateTime.now();
  final ScrollController _scrollController = ScrollController();
  final ScrollController _headerScrollController = ScrollController();
  final ScrollController _contentScrollController = ScrollController();
  bool _isSyncing = false;

  @override
  void initState() {
    super.initState();
    _loadData();
    _setupScrollSync();
  }

  void _setupScrollSync() {
    _headerScrollController.addListener(() {
      if (!_isSyncing &&
          _headerScrollController.hasClients &&
          _contentScrollController.hasClients) {
        _isSyncing = true;
        _contentScrollController.jumpTo(_headerScrollController.offset);
        _isSyncing = false;
      }
    });

    _contentScrollController.addListener(() {
      if (!_isSyncing &&
          _contentScrollController.hasClients &&
          _headerScrollController.hasClients) {
        _isSyncing = true;
        _headerScrollController.jumpTo(_contentScrollController.offset);
        _isSyncing = false;
      }
    });
  }

  Future<void> _loadData() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final bookingProvider =
        Provider.of<BookingProvider>(context, listen: false);

    if (authProvider.token != null && authProvider.user?.companyId != null) {
      await Future.wait([
        bookingProvider.fetchCompanyBookings(
          authProvider.token!,
          authProvider.user!.companyId!,
        ),
        bookingProvider.fetchCompanyStaff(
          authProvider.token!,
          authProvider.user!.companyId!,
        ),
      ]);
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);
    final bookingProvider = Provider.of<BookingProvider>(context);

    return Scaffold(
      backgroundColor: const Color(0xFFF9FAFB), // Light gray background
      appBar: AppBar(
        backgroundColor: const Color(0xFF1F1F1F), // Dark gray/black
        foregroundColor: Colors.white,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Company Calendar',
              style: TextStyle(
                color: Colors.white,
                fontWeight: FontWeight.bold,
              ),
            ),
            Text(
              authProvider.user?.companyName ?? '',
              style: const TextStyle(
                color: Color(0xFFB0B0B0),
                fontSize: 12,
              ),
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.today, color: Colors.white),
            onPressed: () {
              setState(() {
                _selectedDate = DateTime.now();
              });
              _loadData();
            },
            tooltip: 'Today',
          ),
          IconButton(
            icon: const Icon(Icons.person, color: Colors.white),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: Column(
        children: [
          // Date selector
          _buildDateSelector(),

          // Calendar grid
          Expanded(
            child: bookingProvider.isLoading
                ? const Center(child: CircularProgressIndicator())
                : bookingProvider.companyStaff.isEmpty
                    ? _buildEmptyState()
                    : _buildCalendarGrid(bookingProvider),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push('/bookings/create'),
        backgroundColor: const Color(0xFF1F1F1F),
        foregroundColor: Colors.white,
        tooltip: 'New Booking',
        child: const Icon(Icons.add),
      ),
    );
  }

  Widget _buildDateSelector() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 16),
      decoration: const BoxDecoration(
        color: Colors.white,
        border: Border(
          bottom: BorderSide(
            color: Color(0xFFE0E0E0),
            width: 1,
          ),
        ),
        boxShadow: [
          BoxShadow(
            color: Color(0x0A000000),
            blurRadius: 4,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left, color: Color(0xFF1F1F1F)),
            onPressed: () {
              setState(() {
                _selectedDate = _selectedDate.subtract(const Duration(days: 1));
              });
              _loadData();
            },
          ),
          InkWell(
            onTap: () async {
              final date = await showDatePicker(
                context: context,
                initialDate: _selectedDate,
                firstDate: DateTime.now().subtract(const Duration(days: 365)),
                lastDate: DateTime.now().add(const Duration(days: 365)),
              );
              if (date != null) {
                setState(() {
                  _selectedDate = date;
                });
                _loadData();
              }
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
              decoration: BoxDecoration(
                color: const Color(0xFF1F1F1F),
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                DateFormat('EEEE, MMMM d, y').format(_selectedDate),
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 15,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right, color: Color(0xFF1F1F1F)),
            onPressed: () {
              setState(() {
                _selectedDate = _selectedDate.add(const Duration(days: 1));
              });
              _loadData();
            },
          ),
        ],
      ),
    );
  }

  Widget _buildCalendarGrid(BookingProvider bookingProvider) {
    final bookingsForDate = bookingProvider.getBookingsForDate(_selectedDate);
    final staff = bookingProvider.companyStaff;

    // Generate time slots (9 AM to 8 PM, every 30 minutes)
    final timeSlots = _generateTimeSlots();

    return Container(
      margin: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(8),
        boxShadow: const [
          BoxShadow(
            color: Color(0x0A000000),
            blurRadius: 8,
            offset: Offset(0, 2),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(8),
        child: Column(
          children: [
            // Fixed header row with staff avatars
            Row(
              children: [
                // Time column header (fixed)
                Container(
                  width: 80,
                  height: 100,
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: const Color(0xFF0F0F0F),
                    border: Border.all(color: const Color(0xFF404040)),
                  ),
                  child: const Center(
                    child: Text(
                      'Time',
                      style: TextStyle(
                        color: Colors.white,
                        fontWeight: FontWeight.bold,
                        fontSize: 14,
                      ),
                    ),
                  ),
                ),
                // Scrollable staff headers
                Expanded(
                  child: SingleChildScrollView(
                    controller: _headerScrollController,
                    scrollDirection: Axis.horizontal,
                    child: Row(
                      children: staff
                          .map((staffMember) => _buildStaffHeader(staffMember))
                          .toList(),
                    ),
                  ),
                ),
              ],
            ),
            // Scrollable time rows with fixed time column
            Expanded(
              child: SingleChildScrollView(
                controller: _scrollController,
                scrollDirection: Axis.vertical,
                child: Row(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    // Fixed time column
                    Column(
                      children: timeSlots
                          .map((timeSlot) => _buildTimeLabel(timeSlot))
                          .toList(),
                    ),
                    // Scrollable content
                    Expanded(
                      child: SingleChildScrollView(
                        controller: _contentScrollController,
                        scrollDirection: Axis.horizontal,
                        child: Column(
                          children: timeSlots.map((timeSlot) {
                            return Row(
                              children: staff
                                  .map((staffMember) => _buildTimeCell(
                                        timeSlot,
                                        staffMember,
                                        bookingsForDate,
                                      ))
                                  .toList(),
                            );
                          }).toList(),
                        ),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildTimeLabel(String timeSlot) {
    return Container(
      width: 80,
      height: 60,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: const Color(0xFFF5F5F5),
        border: Border.all(color: const Color(0xFFE0E0E0)),
      ),
      child: Center(
        child: Text(
          timeSlot,
          style: const TextStyle(
            color: Color(0xFF1F1F1F),
            fontWeight: FontWeight.w600,
            fontSize: 13,
          ),
        ),
      ),
    );
  }

  Widget _buildStaffHeader(Staff staff) {
    final bookingsForDate = Provider.of<BookingProvider>(context, listen: false)
        .getBookingsForDate(_selectedDate);

    // Calculate occupancy percentage
    final staffBookings =
        bookingsForDate.where((b) => b.staffId == staff.id).toList();
    final totalMinutes = _calculateTotalBookingMinutes(staffBookings);
    final workDayMinutes = 11 * 60; // 9 AM to 8 PM = 11 hours
    final occupancyPercent =
        (totalMinutes / workDayMinutes * 100).clamp(0.0, 100.0);

    return Container(
      width: 200,
      height: 100,
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 6),
      decoration: BoxDecoration(
        color: const Color(0xFF1F1F1F),
        border: Border.all(color: const Color(0xFF404040)),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        mainAxisSize: MainAxisSize.min,
        children: [
          // Avatar
          CircleAvatar(
            radius: 16,
            backgroundColor: const Color(0xFF404040),
            foregroundColor: Colors.white,
            backgroundImage: staff.avatar != null && staff.avatar!.isNotEmpty
                ? NetworkImage(staff.avatar!)
                : null,
            child: staff.avatar == null || staff.avatar!.isEmpty
                ? Text(
                    staff.name.isNotEmpty ? staff.name[0].toUpperCase() : '?',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 14,
                    ),
                  )
                : null,
          ),
          const SizedBox(height: 3),
          // Name
          Text(
            staff.name,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 11,
            ),
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          // Specialization
          if (staff.specialization != null && staff.specialization!.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(top: 1),
              child: Text(
                staff.specialization!,
                style: const TextStyle(
                  color: Color(0xFFB0B0B0),
                  fontSize: 8,
                ),
                textAlign: TextAlign.center,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
              ),
            ),
          const SizedBox(height: 3),
          // Occupancy bar
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 4),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Expanded(
                  child: Container(
                    height: 3,
                    decoration: BoxDecoration(
                      color: const Color(0xFF404040),
                      borderRadius: BorderRadius.circular(2),
                    ),
                    child: FractionallySizedBox(
                      alignment: Alignment.centerLeft,
                      widthFactor: occupancyPercent / 100,
                      child: Container(
                        decoration: BoxDecoration(
                          color: _getOccupancyColor(occupancyPercent),
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 3),
                Text(
                  '${occupancyPercent.toInt()}%',
                  style: const TextStyle(
                    color: Color(0xFFB0B0B0),
                    fontSize: 8,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  int _calculateTotalBookingMinutes(List<Booking> bookings) {
    int totalMinutes = 0;
    for (var booking in bookings) {
      final start = _parseTime(booking.startTime);
      final end = _parseTime(booking.endTime);
      if (start != null && end != null) {
        totalMinutes += end.difference(start).inMinutes;
      }
    }
    return totalMinutes;
  }

  DateTime? _parseTime(String time) {
    try {
      final parts = time.split(':');
      if (parts.length >= 2) {
        final hour = int.parse(parts[0]);
        final minute = int.parse(parts[1]);
        return DateTime(2000, 1, 1, hour, minute);
      }
    } catch (e) {
      // Ignore parse errors
    }
    return null;
  }

  Color _getOccupancyColor(double percent) {
    if (percent >= 80) {
      return const Color(0xFFEF4444); // Red
    } else if (percent >= 50) {
      return const Color(0xFFF59E0B); // Yellow/Amber
    } else {
      return const Color(0xFF10B981); // Green
    }
  }

  Widget _buildTimeCell(String timeSlot, Staff staff, List<Booking> bookings) {
    // Find booking for this time slot and staff member
    final booking = bookings.firstWhere(
      (b) =>
          b.staffId == staff.id &&
          _isTimeInRange(timeSlot, b.startTime, b.endTime),
      orElse: () => Booking(
        id: '',
        customerId: '',
        customerName: '',
        companyId: '',
        companyName: '',
        serviceId: '',
        serviceName: '',
        bookingDate: DateTime.now(),
        startTime: '',
        endTime: '',
        status: '',
        price: 0,
        createdAt: DateTime.now(),
      ),
    );

    final hasBooking = booking.id.isNotEmpty;
    final opacity = _getBookingOpacity(booking.status);

    // Only show booking details if this is the start time slot
    final isStartSlot = hasBooking && timeSlot == booking.startTime;

    return InkWell(
      onTap: hasBooking ? () => context.push('/bookings/${booking.id}') : null,
      child: Container(
        width: 200,
        height: 60,
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 4),
        decoration: BoxDecoration(
          color: hasBooking
              ? _getStatusColor(booking.status).withOpacity(opacity)
              : Colors.white,
          border: Border.all(color: const Color(0xFFE0E0E0)),
        ),
        child: hasBooking && isStartSlot
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Customer name with bold styling
                  Text(
                    booking.customerName.toUpperCase(),
                    style: const TextStyle(
                      color: Color(0xFF1F1F1F),
                      fontWeight: FontWeight.bold,
                      fontSize: 11,
                      height: 1.2,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 1),
                  // Service name
                  Text(
                    booking.serviceName,
                    style: const TextStyle(
                      color: Color(0xFF666666),
                      fontSize: 10,
                      height: 1.2,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  const SizedBox(height: 1),
                  // Time range
                  Text(
                    '${booking.startTime} - ${booking.endTime}',
                    style: const TextStyle(
                      color: Color(0xFF404040),
                      fontSize: 9,
                      fontWeight: FontWeight.w500,
                      height: 1.2,
                    ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              )
            : null,
      ),
    );
  }

  double _getBookingOpacity(String status) {
    // Pending bookings have reduced opacity
    if (status == 'pending') {
      return 0.7;
    }
    return 1.0;
  }

  Widget _buildEmptyState() {
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(
              Icons.people_outline,
              size: 64,
              color: Theme.of(context).colorScheme.secondary,
            ),
            const SizedBox(height: 16),
            Text(
              'No staff members',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'Add staff members to view the calendar',
              style: Theme.of(context).textTheme.bodyMedium,
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }

  List<String> _generateTimeSlots() {
    final slots = <String>[];
    for (int hour = 9; hour < 20; hour++) {
      slots.add('${hour.toString().padLeft(2, '0')}:00');
      slots.add('${hour.toString().padLeft(2, '0')}:30');
    }
    return slots;
  }

  bool _isTimeInRange(String timeSlot, String startTime, String endTime) {
    // Simple time comparison (format: "HH:mm")
    return timeSlot.compareTo(startTime) >= 0 &&
        timeSlot.compareTo(endTime) < 0;
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'confirmed':
        return const Color(0xFF10B981); // Green
      case 'pending':
        return const Color(0xFFF59E0B); // Amber/Yellow
      case 'cancelled':
        return const Color(0xFFEF4444); // Red
      case 'completed':
        return const Color(0xFF3B82F6); // Blue
      default:
        return const Color(0xFFD1D5DB); // Gray
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    _headerScrollController.dispose();
    _contentScrollController.dispose();
    super.dispose();
  }
}
