import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:go_router/go_router.dart';
import '../../providers/auth_provider.dart';
import '../../providers/booking_provider.dart';

class CreateBookingScreen extends StatefulWidget {
  const CreateBookingScreen({super.key});

  @override
  State<CreateBookingScreen> createState() => _CreateBookingScreenState();
}

class _CreateBookingScreenState extends State<CreateBookingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _notesController = TextEditingController();
  
  DateTime? _selectedDate;
  TimeOfDay? _selectedTime;
  String? _selectedCompanyId;
  String? _selectedServiceId;
  String? _selectedStaffId;

  @override
  void dispose() {
    _notesController.dispose();
    super.dispose();
  }

  Future<void> _selectDate() async {
    final date = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    
    if (date != null) {
      setState(() {
        _selectedDate = date;
      });
    }
  }

  Future<void> _selectTime() async {
    final time = await showTimePicker(
      context: context,
      initialTime: TimeOfDay.now(),
    );
    
    if (time != null) {
      setState(() {
        _selectedTime = time;
      });
    }
  }

  Future<void> _createBooking() async {
    if (_formKey.currentState!.validate()) {
      if (_selectedDate == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please select a date')),
        );
        return;
      }
      if (_selectedTime == null) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Please select a time')),
        );
        return;
      }

      final authProvider = Provider.of<AuthProvider>(context, listen: false);
      final bookingProvider = Provider.of<BookingProvider>(context, listen: false);
      
      if (authProvider.token != null) {
        final bookingData = {
          'company_id': _selectedCompanyId ?? '1',
          'service_id': _selectedServiceId ?? '1',
          'staff_id': _selectedStaffId,
          'booking_date': _selectedDate!.toIso8601String(),
          'start_time': '${_selectedTime!.hour.toString().padLeft(2, '0')}:${_selectedTime!.minute.toString().padLeft(2, '0')}',
          'notes': _notesController.text.trim(),
        };

        final success = await bookingProvider.createBooking(
          authProvider.token!,
          bookingData,
        );

        if (mounted) {
          if (success) {
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Booking created successfully')),
            );
            context.pop();
          } else {
            ScaffoldMessenger.of(context).showSnackBar(
              SnackBar(
                content: Text(bookingProvider.error ?? 'Failed to create booking'),
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

    return Scaffold(
      appBar: AppBar(
        title: const Text('New Booking'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16),
        child: Form(
          key: _formKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Booking Information',
                        style: Theme.of(context).textTheme.titleLarge,
                      ),
                      const SizedBox(height: 16),
                      
                      // Company selection (placeholder)
                      DropdownButtonFormField<String>(
                        decoration: const InputDecoration(
                          labelText: 'Salon',
                          prefixIcon: Icon(Icons.business),
                        ),
                        initialValue: _selectedCompanyId,
                        items: const [
                          DropdownMenuItem(value: '1', child: Text('Salon 1')),
                          DropdownMenuItem(value: '2', child: Text('Salon 2')),
                        ],
                        onChanged: (value) {
                          setState(() {
                            _selectedCompanyId = value;
                          });
                        },
                        validator: (value) {
                          if (value == null) {
                            return 'Please select a salon';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      
                      // Service selection (placeholder)
                      DropdownButtonFormField<String>(
                        decoration: const InputDecoration(
                          labelText: 'Service',
                          prefixIcon: Icon(Icons.cut),
                        ),
                        initialValue: _selectedServiceId,
                        items: const [
                          DropdownMenuItem(value: '1', child: Text('Haircut')),
                          DropdownMenuItem(value: '2', child: Text('Hair Coloring')),
                          DropdownMenuItem(value: '3', child: Text('Manicure')),
                        ],
                        onChanged: (value) {
                          setState(() {
                            _selectedServiceId = value;
                          });
                        },
                        validator: (value) {
                          if (value == null) {
                            return 'Please select a service';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      
                      // Staff selection (optional)
                      DropdownButtonFormField<String>(
                        decoration: const InputDecoration(
                          labelText: 'Staff (Optional)',
                          prefixIcon: Icon(Icons.person),
                        ),
                        initialValue: _selectedStaffId,
                        items: const [
                          DropdownMenuItem(value: '1', child: Text('Any Available')),
                          DropdownMenuItem(value: '2', child: Text('Staff 1')),
                          DropdownMenuItem(value: '3', child: Text('Staff 2')),
                        ],
                        onChanged: (value) {
                          setState(() {
                            _selectedStaffId = value;
                          });
                        },
                      ),
                      const SizedBox(height: 16),
                      
                      // Date selection
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.calendar_today),
                        title: Text(_selectedDate == null
                            ? 'Select Date'
                            : _selectedDate.toString().split(' ')[0]),
                        trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                        onTap: _selectDate,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                          side: BorderSide(color: Theme.of(context).dividerColor),
                        ),
                      ),
                      const SizedBox(height: 16),
                      
                      // Time selection
                      ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.access_time),
                        title: Text(_selectedTime == null
                            ? 'Select Time'
                            : '${_selectedTime!.hour.toString().padLeft(2, '0')}:${_selectedTime!.minute.toString().padLeft(2, '0')}'),
                        trailing: const Icon(Icons.arrow_forward_ios, size: 16),
                        onTap: _selectTime,
                        shape: RoundedRectangleBorder(
                          borderRadius: BorderRadius.circular(8),
                          side: BorderSide(color: Theme.of(context).dividerColor),
                        ),
                      ),
                      const SizedBox(height: 16),
                      
                      // Notes
                      TextFormField(
                        controller: _notesController,
                        decoration: const InputDecoration(
                          labelText: 'Notes (Optional)',
                          prefixIcon: Icon(Icons.note),
                          alignLabelWithHint: true,
                        ),
                        maxLines: 3,
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: bookingProvider.isLoading ? null : _createBooking,
                child: bookingProvider.isLoading
                    ? const SizedBox(
                        height: 20,
                        width: 20,
                        child: CircularProgressIndicator(strokeWidth: 2),
                      )
                    : const Text('Create Booking'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
