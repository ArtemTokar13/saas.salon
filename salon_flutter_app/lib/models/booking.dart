class Booking {
  final String id;
  final String customerId;
  final String customerName;
  final String? customerPhone;
  final String companyId;
  final String companyName;
  final String serviceId;
  final String serviceName;
  final String? staffId;
  final String? staffName;
  final DateTime bookingDate;
  final String startTime;
  final String endTime;
  final String status;
  final double price;
  final String? notes;
  final DateTime createdAt;

  Booking({
    required this.id,
    required this.customerId,
    required this.customerName,
    this.customerPhone,
    required this.companyId,
    required this.companyName,
    required this.serviceId,
    required this.serviceName,
    this.staffId,
    this.staffName,
    required this.bookingDate,
    required this.startTime,
    required this.endTime,
    required this.status,
    required this.price,
    this.notes,
    required this.createdAt,
  });

  factory Booking.fromJson(Map<String, dynamic> json) {
    return Booking(
      id: json['id'].toString(),
      customerId: json['customer_id'].toString(),
      customerName: json['customer_name'] ?? '',
      customerPhone: json['customer_phone'],
      companyId: json['company_id'].toString(),
      companyName: json['company_name'] ?? '',
      serviceId: json['service_id'].toString(),
      serviceName: json['service_name'] ?? '',
      staffId: json['staff_id']?.toString(),
      staffName: json['staff_name'],
      bookingDate: DateTime.parse(json['booking_date']),
      startTime: json['start_time'],
      endTime: json['end_time'],
      status: json['status'],
      price: double.parse(json['price'].toString()),
      notes: json['notes'],
      createdAt: DateTime.parse(json['created_at']),
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'customer_id': customerId,
      'company_id': companyId,
      'service_id': serviceId,
      'staff_id': staffId,
      'booking_date': bookingDate.toIso8601String(),
      'start_time': startTime,
      'end_time': endTime,
      'status': status,
      'price': price,
      'notes': notes,
    };
  }

  String get statusDisplay {
    switch (status) {
      case 'pending':
        return 'Pending';
      case 'confirmed':
        return 'Confirmed';
      case 'cancelled':
        return 'Cancelled';
      case 'completed':
        return 'Completed';
      default:
        return status;
    }
  }
}
