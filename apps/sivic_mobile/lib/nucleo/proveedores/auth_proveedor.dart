import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:dio/dio.dart';
import '../red/cliente_http.dart';
import '../../compartido/modelos/usuario.modelo.dart';

class EstadoAuth {
  final Usuario? usuario;
  final bool     cargando;
  final String?  error;

  const EstadoAuth({this.usuario, this.cargando = false, this.error});

  bool get autenticado => usuario != null;
  EstadoAuth copyWith({Usuario? usuario, bool? cargando, String? error}) =>
      EstadoAuth(usuario: usuario ?? this.usuario, cargando: cargando ?? this.cargando, error: error);
}

class AuthNotifier extends StateNotifier<EstadoAuth> {
  final Dio _http;
  AuthNotifier(this._http) : super(const EstadoAuth());

  Future<void> cargarSesionGuardada() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString('sivic_token');
    if (token == null) return;
    try {
      final resp = await _http.get('/auth/perfil/');
      state = EstadoAuth(usuario: Usuario.fromJson(resp.data as Map<String, dynamic>));
    } catch (_) {
      await prefs.remove('sivic_token');
    }
  }

  Future<bool> iniciarSesion(String email, String password) async {
    state = const EstadoAuth(cargando: true);
    try {
      final resp = await _http.post('/auth/login/', data: {'email': email, 'password': password});
      final datos = resp.data as Map<String, dynamic>;
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('sivic_token', datos['token'] as String);
      state = EstadoAuth(usuario: Usuario.fromJson(datos['usuario'] as Map<String, dynamic>));
      return true;
    } on DioException catch (e) {
      final msg = (e.response?.data as Map?)?['detail'] ?? 'Error de conexión';
      state = EstadoAuth(error: msg.toString());
      return false;
    }
  }

  Future<void> cerrarSesion() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove('sivic_token');
    state = const EstadoAuth();
  }
}

final httpProvider    = Provider<Dio>((ref) => crearClienteHttp());
final authProvider    = StateNotifierProvider<AuthNotifier, EstadoAuth>(
  (ref) => AuthNotifier(ref.read(httpProvider)),
);
