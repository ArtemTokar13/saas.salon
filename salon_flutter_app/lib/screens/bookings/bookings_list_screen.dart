import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../providers/booking_provider.dart';

class BookingsListScreen extends StatefulWidget {
  const BookingsListScreen({super.key});

  @override
  State<BookingsListScreen> createState() => _BookingsListScreenState();
}

class _BookingsListScreenState extends State<BookingsListScreen> {
  @override
  void initState() {
    super.initState();
    _loadBookings();
  }

  Future<void> _loadBookings() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final bookingProvider = Provider.of<BookingProvider>(context, listen: false);
    
    if (authProvider.token != null) {
      await bookingProvider.fetchBookings(authProvider.token!);
    }
  }

  @override
  Widget build(BuildContext context) {
    final bookingProvider = Provider.of<BookingProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('My Bookings'),
      ),
      body: RefreshIndicator(
        onRefresh: _loadBookings,
        child: bookingProvider.isLoading
            ? const Center(child: CircularProgressIndicator())
            : bookingProvider.bookings.isEmpty
                ? Center(
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(
                          Icons.calendar_today,
                          size: 80,
                          color: Theme.of(context).colorScheme.secondary,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'No bookings yet',
                          style: Theme.of(context).textTheme.titleLarge,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Create your first booking',
                          style: Theme.of(context).textTheme.bodyMedium,
                        ),
                        const SizedBox(height: 24),
                        ElevatedButton.icon(
                          onPressed: () => context.push('/bookings/create'),
                          icon: const Icon(Icons.add),
                          label: const Text('New Booking'),
                        ),
                      ],
                    ),
                  )
                : ListView.builder(
                    padding: const EdgeInsets.all(16),
                    itemCount: bookingProvider.bookings.length,
                    itemBuilder: (context, index) {
                      final booking = bookingProvider.bookings[index];
                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: ListTile(
                          leading: CircleAvatar(
                            child: Text(booking.serviceName[0].toUpperCase()),
                          ),
                          title: Text(booking.serviceName),
                          subtitle: Text(
                            '${booking.companyName}\n${booking.bookingDate.toString().split(' ')[0]} at ${booking.startTime}',
                          ),
                          isThreeLine: true,
                          trailing: Chip(
                            label: Text(booking.statusDisplay),
                            backgroundColor: _getStatusColor(booking.status),
                          ),
                          onTap: () => context.push('/bookings/${booking.id}'),
                        ),
                      );
                    },
                  ),
      ),
      floatingActionButton: FloatingActionButton(
        onPressed: () => context.push('/bookings/create'),
        child: const Icon(Icons.add),
      ),
    );
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
}
