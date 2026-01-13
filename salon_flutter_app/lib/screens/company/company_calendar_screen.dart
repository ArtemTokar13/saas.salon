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

  @override
  void initState() {
    super.initState();
    _loadData();
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
      appBar: AppBar(
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('Company Calendar'),
            Text(
              authProvider.user?.companyName ?? '',
              style: Theme.of(context).textTheme.bodySmall,
            ),
          ],
        ),
        actions: [
          IconButton(
            icon: const Icon(Icons.today),
            onPressed: () {
              setState(() {
                _selectedDate = DateTime.now();
              });
              _loadData();
            },
            tooltip: 'Today',
          ),
          IconButton(
            icon: const Icon(Icons.person),
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
        child: const Icon(Icons.add),
        tooltip: 'New Booking',
      ),
    );
  }

  Widget _buildDateSelector() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 16),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.surface,
        border: Border(
          bottom: BorderSide(
            color: Theme.of(context).dividerColor,
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
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
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              decoration: BoxDecoration(
                color: Theme.of(context).colorScheme.primaryContainer,
                borderRadius: BorderRadius.circular(8),
              ),
              child: Text(
                DateFormat('EEEE, MMMM d, y').format(_selectedDate),
                style: Theme.of(context).textTheme.titleMedium?.copyWith(
                      color: Theme.of(context).colorScheme.onPrimaryContainer,
                    ),
              ),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right),
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

    return SingleChildScrollView(
      controller: _scrollController,
      scrollDirection: Axis.vertical,
      child: SingleChildScrollView(
        scrollDirection: Axis.horizontal,
        child: Container(
          padding: const EdgeInsets.all(8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header row with staff names
              Row(
                children: [
                  // Time column header
                  Container(
                    width: 80,
                    height: 60,
                    padding: const EdgeInsets.all(8),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primaryContainer,
                      border: Border.all(color: Theme.of(context).dividerColor),
                    ),
                    child: Center(
                      child: Text(
                        'Time',
                        style: Theme.of(context).textTheme.titleSmall?.copyWith(
                              fontWeight: FontWeight.bold,
                            ),
                      ),
                    ),
                  ),
                  // Staff columns
                  ...staff.map((staffMember) => _buildStaffHeader(staffMember)),
                ],
              ),
              // Time rows
              ...timeSlots.map((timeSlot) => _buildTimeRow(
                    timeSlot,
                    staff,
                    bookingsForDate,
                  )),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildStaffHeader(Staff staff) {
    return Container(
      width: 150,
      height: 60,
      padding: const EdgeInsets.all(8),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.secondaryContainer,
        border: Border.all(color: Theme.of(context).dividerColor),
      ),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Text(
            staff.name,
            style: Theme.of(context).textTheme.titleSmall?.copyWith(
                  fontWeight: FontWeight.bold,
                ),
            textAlign: TextAlign.center,
            maxLines: 1,
            overflow: TextOverflow.ellipsis,
          ),
          if (staff.specialization != null)
            Text(
              staff.specialization!,
              style: Theme.of(context).textTheme.bodySmall,
              textAlign: TextAlign.center,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
        ],
      ),
    );
  }

  Widget _buildTimeRow(
      String timeSlot, List<Staff> staff, List<Booking> bookings) {
    return Row(
      children: [
        // Time label
        Container(
          width: 80,
          height: 60,
          padding: const EdgeInsets.all(8),
          decoration: BoxDecoration(
            color: Theme.of(context).colorScheme.surface,
            border: Border.all(color: Theme.of(context).dividerColor),
          ),
          child: Center(
            child: Text(
              timeSlot,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w500,
                  ),
            ),
          ),
        ),
        // Staff cells
        ...staff.map((staffMember) => _buildTimeCell(
              timeSlot,
              staffMember,
              bookings,
            )),
      ],
    );
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

    return InkWell(
      onTap: hasBooking ? () => context.push('/bookings/${booking.id}') : null,
      child: Container(
        width: 150,
        height: 60,
        padding: const EdgeInsets.all(4),
        decoration: BoxDecoration(
          color: hasBooking
              ? _getStatusColor(booking.status)
              : Theme.of(context).colorScheme.surface,
          border: Border.all(color: Theme.of(context).dividerColor),
        ),
        child: hasBooking
            ? Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    booking.customerName,
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    booking.serviceName,
                    style: Theme.of(context).textTheme.bodySmall,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                  Text(
                    '${booking.startTime} - ${booking.endTime}',
                    style: Theme.of(context).textTheme.bodySmall?.copyWith(
                          fontSize: 10,
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
        return Colors.green.shade100;
      case 'pending':
        return Colors.orange.shade100;
      case 'cancelled':
        return Colors.red.shade100;
      case 'completed':
        return Colors.blue.shade100;
      default:
        return Colors.grey.shade100;
    }
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }
}
