import 'package:dio/dio.dart';
import 'package:shared_preferences/shared_preferences.dart';

const String _urlBase = 'http://10.0.2.2:8000/api'; // emulador Android → localhost

Dio crearClienteHttp() {
  final dio = Dio(BaseOptions(
    baseUrl: _urlBase,
    connectTimeout: const Duration(seconds: 10),
    receiveTimeout: const Duration(seconds: 15),
    headers: {'Content-Type': 'application/json'},
  ));

  dio.interceptors.add(InterceptorsWrapper(
    onRequest: (options, handler) async {
      final prefs = await SharedPreferences.getInstance();
      final token = prefs.getString('sivic_token');
      if (token != null) {
        options.headers['Authorization'] = 'Bearer $token';
      }
      return handler.next(options);
    },
    onError: (error, handler) {
      return handler.next(error);
    },
  ));

  return dio;
}
