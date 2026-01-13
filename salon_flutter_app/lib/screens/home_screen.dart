import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../providers/auth_provider.dart';
import '../providers/booking_provider.dart';
import 'company/company_calendar_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  @override
  void initState() {
    super.initState();
    _loadData();
  }

  Future<void> _loadData() async {
    final authProvider = Provider.of<AuthProvider>(context, listen: false);
    final bookingProvider =
        Provider.of<BookingProvider>(context, listen: false);

    if (authProvider.token != null) {
      // Load different data based on user type
      if (authProvider.user?.hasCompany ?? false) {
        // Salon owner/staff - load company bookings
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
      } else {
        // Customer - load their own bookings
        await bookingProvider.fetchBookings(authProvider.token!);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);

    // Route to different screens based on user type
    if (authProvider.user?.hasCompany ?? false) {
      // Show company calendar for salon owners/staff
      return const CompanyCalendarScreen();
    } else {
      // Show customer home for regular customers
      return _buildCustomerHome(context);
    }
  }

  Widget _buildCustomerHome(BuildContext context) {
    final authProvider = Provider.of<AuthProvider>(context);
    final bookingProvider = Provider.of<BookingProvider>(context);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Salon Booking'),
        actions: [
          IconButton(
            icon: const Icon(Icons.person),
            onPressed: () => context.push('/profile'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _loadData,
        child: SingleChildScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Welcome card
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Row(
                    children: [
                      const CircleAvatar(
                        radius: 30,
                        child: Icon(Icons.person, size: 30),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Welcome back!',
                              style: Theme.of(context).textTheme.titleMedium,
                            ),
                            Text(
                              authProvider.user?.fullName ?? 'Guest',
                              style: Theme.of(context).textTheme.bodyLarge,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),

              // Quick actions
              Text(
                'Quick Actions',
                style: Theme.of(context).textTheme.titleLarge,
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: _QuickActionCard(
                      icon: Icons.calendar_today,
                      title: 'New Booking',
                      onTap: () => context.push('/bookings/create'),
                    ),
                  ),
                  const SizedBox(width: 16),
                  Expanded(
                    child: _QuickActionCard(
                      icon: Icons.calendar_month,
                      title: 'Calendar',
                      onTap: () => context.push('/calendar'),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Expanded(
                    child: _QuickActionCard(
                      icon: Icons.list,
                      title: 'My Bookings',
                      onTap: () => context.push('/bookings'),
                    ),
                  ),
                  const SizedBox(width: 16),
                  const Expanded(child: SizedBox()), // Empty space for symmetry
                ],
              ),
              const SizedBox(height: 24),

              // Recent bookings
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Text(
                    'Recent Bookings',
                    style: Theme.of(context).textTheme.titleLarge,
                  ),
                  TextButton(
                    onPressed: () => context.push('/bookings'),
                    child: const Text('See All'),
                  ),
                ],
              ),
              const SizedBox(height: 16),

              if (bookingProvider.isLoading)
                const Center(child: CircularProgressIndicator())
              else if (bookingProvider.bookings.isEmpty)
                Center(
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: Column(
                      children: [
                        Icon(
                          Icons.calendar_today,
                          size: 64,
                          color: Theme.of(context).colorScheme.secondary,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          'No bookings yet',
                          style: Theme.of(context).textTheme.titleMedium,
                        ),
                        const SizedBox(height: 8),
                        Text(
                          'Create your first booking to get started',
                          style: Theme.of(context).textTheme.bodyMedium,
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  ),
                )
              else
                ...bookingProvider.bookings.take(3).map((booking) {
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
                }),
            ],
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => context.push('/bookings/create'),
        icon: const Icon(Icons.add),
        label: const Text('New Booking'),
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

class _QuickActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final VoidCallback onTap;

  const _QuickActionCard({
    required this.icon,
    required this.title,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(12),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            children: [
              Icon(icon,
                  size: 40, color: Theme.of(context).colorScheme.primary),
              const SizedBox(height: 8),
              Text(
                title,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.titleSmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
