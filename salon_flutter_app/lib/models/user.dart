class User {
  final String id;
  final String email;
  final String? firstName;
  final String? lastName;
  final String? phone;
  final String? avatar;
  final bool isAdmin;
  final String? companyId;
  final String? companyName;
  final String? staffId;
  final String? staffName;

  User({
    required this.id,
    required this.email,
    this.firstName,
    this.lastName,
    this.phone,
    this.avatar,
    this.isAdmin = false,
    this.companyId,
    this.companyName,
    this.staffId,
    this.staffName,
  });

  factory User.fromJson(Map<String, dynamic> json) {
    return User(
      id: json['id'].toString(),
      email: json['email'],
      firstName: json['first_name'],
      lastName: json['last_name'],
      phone: json['phone'],
      avatar: json['avatar'],
      isAdmin: json['is_admin'] ?? false,
      companyId: json['company_id']?.toString(),
      companyName: json['company_name'],
      staffId: json['staff_id']?.toString(),
      staffName: json['staff_name'],
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'email': email,
      'first_name': firstName,
      'last_name': lastName,
      'phone': phone,
      'avatar': avatar,
      'is_admin': isAdmin,
      'company_id': companyId,
      'company_name': companyName,
      'staff_id': staffId,
      'staff_name': staffName,
    };
  }

  String get fullName {
    if (firstName != null && lastName != null) {
      return '$firstName $lastName';
    }
    return email;
  }

  // Check if user is salon owner/admin
  bool get isCompanyAdmin => companyId != null && isAdmin;

  // Check if user is staff member
  bool get isStaff => staffId != null;

  // Check if user works for a company (admin or staff)
  bool get hasCompany => companyId != null;

  // Check if user is just a customer
  bool get isCustomer => !hasCompany;
}
