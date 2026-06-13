import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:dio/dio.dart';
import 'auth_proveedor.dart';
import '../../compartido/modelos/evento.modelo.dart';

final eventosProvider = FutureProvider.family<List<Evento>, String?>((ref, estado) async {
  final http = ref.read(httpProvider);
  final params = estado != null ? {'estado': estado} : <String, dynamic>{};
  final resp = await http.get('/eventos/', queryParameters: params);
  return (resp.data as List).map((e) => Evento.fromJson(e as Map<String, dynamic>)).toList();
});
