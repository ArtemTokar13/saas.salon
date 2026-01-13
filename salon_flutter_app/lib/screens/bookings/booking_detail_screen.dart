import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../providers/booking_provider.dart';

class BookingDetailScreen extends StatefulWidget {
  final String bookingId;

  const BookingDetailScreen({super.key, required this.bookingId});

  @override
  State<BookingDetailScreen> createState() => _BookingDetailScreenState();
}

class _BookingDetailScreenState extends State<BookingDetailScreen> {
  @override
  void initState() {
    super.initState();
    _loadBooking();
  }

  Future<void> _loadBooking() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final bookingProvider = Provider.of<BookingProvider>(context, listen: false);
    
    if (authProvider.token != null) {
      await bookingProvider.fetchBookingById(authProvider.token!, widget.bookingId);
    }
  }

  Future<void> _cancelBooking() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Cancel Booking'),
        content: const Text('Are you sure you want to cancel this booking?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('No'),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, true),
            child: const Text('Yes'),
          ),
        ],
      ),
    );

    if (confirmed == true && mounted) {
      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final bookingProvider = Provider.of<BookingProvider>(context, listen: false);
      
      if (authProvider.token != null) {
        final success = await bookingProvider.cancelBooking(
          authProvider.token!,
          widget.bookingId,
        );
        
        if (mounted) {
          if (success) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Booking cancelled successfully')),
            );
            context.pop();
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(bookingProvider.error ?? 'Failed to cancel booking'),
                backgroundColor: Colors.red,
              ),
            );
          }
        }
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final bookingProvider = Provider.of<BookingProvider>(context);
    final booking = bookingProvider.currentBooking;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Booking Details'),
      ),
      body: bookingProvider.isLoading
          ? const Center(child: CircularProgressIndicator())
          : booking == null
              ? const Center(child: Text('Booking not found'))
              : SingleChildScrollView(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Card(
                        child: Padding(
                          padding: const EdgeInsets.all(16),
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Row(
                                children: [
                                  CircleAvatar(
                                    radius: 30,
                                    child: Text(
                                      booking.serviceName[0].toUpperCase(),
                                      style: const TextStyle(fontSize: 24),
                                    ),
                                  ),
                                  const SizedBox(width: 16),
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment: CrossAxisAlignment.start,
                                      children: [
                                        Text(
                                          booking.serviceName,
                                          style: Theme.of(context).textTheme.titleLarge,
                                        ),
                                        Text(
                                          booking.companyName,
                                          style: Theme.of(context).textTheme.bodyLarge,
                                        ),
                                      ],
                                    ),
                                  ),
                                ],
                              ),
                              const Divider(height: 32),
                              _DetailRow(
                                icon: Icons.calendar_today,
                                label: 'Date',
                                value: booking.bookingDate.toString().split(' ')[0],
                              ),
                              const SizedBox(height: 12),
                              _DetailRow(
                                icon: Icons.access_time,
                                label: 'Time',
                                value: '${booking.startTime} - ${booking.endTime}',
                              ),
                              const SizedBox(height: 12),
                              _DetailRow(
                                icon: Icons.person,
                                label: 'Customer',
                                value: booking.customerName,
                              ),
                              if (booking.customerPhone != null) ...[
                                const SizedBox(height: 12),
                                _DetailRow(
                                  icon: Icons.phone,
                                  label: 'Phone',
                                  value: booking.customerPhone!,
                                ),
                              ],
                              if (booking.staffName != null) ...[
                                const SizedBox(height: 12),
                                _DetailRow(
                                  icon: Icons.person_outline,
                                  label: 'Staff',
                                  value: booking.staffName!,
                                ),
                              ],
                              const SizedBox(height: 12),
                              _DetailRow(
                                icon: Icons.attach_money,
                                label: 'Price',
                                value: '\$${booking.price.toStringAsFixed(2)}',
                              ),
                              const SizedBox(height: 12),
                              _DetailRow(
                                icon: Icons.info_outline,
                                label: 'Status',
                                value: booking.statusDisplay,
                              ),
                              if (booking.notes != null) ...[
                                const Divider(height: 32),
                                Text(
                                  'Notes',
                                  style: Theme.of(context).textTheme.titleMedium,
                                ),
                                const SizedBox(height: 8),
                                Text(booking.notes!),
                              ],
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 24),
                      if (booking.status != 'cancelled' && booking.status != 'completed')
                        SizedBox(
                          width: double.infinity,
                          child: ElevatedButton.icon(
                            onPressed: _cancelBooking,
                            icon: const Icon(Icons.cancel),
                            label: const Text('Cancel Booking'),
                            style: ElevatedButton.styleFrom(
                              backgroundColor: Colors.red,
                              foregroundColor: Colors.white,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;

  const _DetailRow({
    required this.icon,
    required this.label,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Icon(icon, size: 20, color: Theme.of(context).colorScheme.secondary),
        const SizedBox(width: 12),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                label,
                style: Theme.of(context).textTheme.bodySmall,
              ),
              Text(
                value,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
            ],
          ),
        ),
      ],
    );
  }
}
