import 'package:flutter/foundation.dart';

class AppLogger {
  static void log(String message, {String? tag}) {
    if (kDebugMode) {
      final timestamp = DateTime.now().toIso8601String();
      final tagStr = tag != null ? '[$tag]' : '';
      print('[$timestamp] $tagStr $message');
    }
  }

  static void error(String message, {dynamic error, StackTrace? stackTrace}) {
    if (kDebugMode) {
      final timestamp = DateTime.now().toIso8601String();
      print('[$timestamp] [ERROR] $message');
      if (error != null) print('Error: $error');
      if (stackTrace != null) print('StackTrace: $stackTrace');
    }
  }

  static void api(String method, String url, {dynamic body, dynamic response}) {
    if (kDebugMode) {
      print('--- API Call ---');
      print('$method $url');
      if (body != null) print('Body: $body');
      if (response != null) print('Response: $response');
      print('--- End API ---');
    }
  }
}
