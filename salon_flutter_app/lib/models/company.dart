class Company {
  final String id;
  final String name;
  final String? description;
  final String? address;
  final String? phone;
  final String? email;
  final String? website;
  final String? logo;
  final Map<String, dynamic>? socialMedia;
  final List<String>? images;

  Company({
    required this.id,
    required this.name,
    this.description,
    this.address,
    this.phone,
    this.email,
    this.website,
    this.logo,
    this.socialMedia,
    this.images,
  });

  factory Company.fromJson(Map<String, dynamic> json) {
    return Company(
      id: json['id'].toString(),
      name: json['name'],
      description: json['description'],
      address: json['address'],
      phone: json['phone'],
      email: json['email'],
      website: json['website'],
      logo: json['logo'],
      socialMedia: json['social_media'],
      images: json['images'] != null ? List<String>.from(json['images']) : null,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'address': address,
      'phone': phone,
      'email': email,
      'website': website,
      'logo': logo,
      'social_media': socialMedia,
      'images': images,
    };
  }
}

class Service {
  final String id;
  final String name;
  final String? description;
  final double price;
  final int duration; // in minutes
  final bool isActive;

  Service({
    required this.id,
    required this.name,
    this.description,
    required this.price,
    required this.duration,
    this.isActive = true,
  });

  factory Service.fromJson(Map<String, dynamic> json) {
    return Service(
      id: json['id'].toString(),
      name: json['name'],
      description: json['description'],
      price: double.parse(json['price'].toString()),
      duration: json['duration'],
      isActive: json['is_active'] ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'description': description,
      'price': price,
      'duration': duration,
      'is_active': isActive,
    };
  }

  String get durationDisplay {
    if (duration < 60) {
      return '$duration min';
    }
    final hours = duration ~/ 60;
    final minutes = duration % 60;
    if (minutes == 0) {
      return '$hours h';
    }
    return '$hours h $minutes min';
  }
}

class Staff {
  final String id;
  final String name;
  final String? email;
  final String? phone;
  final String? avatar;
  final String? specialization;
  final bool isActive;

  Staff({
    required this.id,
    required this.name,
    this.email,
    this.phone,
    this.avatar,
    this.specialization,
    this.isActive = true,
  });

  factory Staff.fromJson(Map<String, dynamic> json) {
    return Staff(
      id: json['id'].toString(),
      name: json['name'] ?? '',
      email: json['email'],
      phone: json['phone'],
      avatar: json['avatar'],
      specialization: json['specialization'],
      isActive: json['is_active'] ?? true,
    );
  }

  Map<String, dynamic> toJson() {
    return {
      'id': id,
      'name': name,
      'email': email,
      'phone': phone,
      'avatar': avatar,
      'specialization': specialization,
      'is_active': isActive,
    };
  }
}
