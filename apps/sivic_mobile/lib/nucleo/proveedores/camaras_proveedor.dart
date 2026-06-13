import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'auth_proveedor.dart';
import '../../compartido/modelos/camara.modelo.dart';

final camarasProvider = FutureProvider<List<Camara>>((ref) async {
  final http = ref.read(httpProvider);
  final resp = await http.get('/camaras/');
  return (resp.data as List)
      .map((e) => Camara.fromJson(e as Map<String, dynamic>))
      .where((c) => c.isActive)
      .toList();
});
