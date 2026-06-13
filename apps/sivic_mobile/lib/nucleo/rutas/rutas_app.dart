import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../proveedores/auth_proveedor.dart';
import '../../pantallas/login/pantalla_login.dart';
import '../../pantallas/camaras/pantalla_camaras.dart';
import '../../pantallas/eventos/pantalla_eventos.dart';
import '../../compartido/widgets/diseno_guardia.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authProvider);

  return GoRouter(
    initialLocation: '/camaras',
    redirect: (context, state) {
      final autenticado = auth.autenticado;
      final enLogin     = state.matchedLocation == '/login';
      if (!autenticado && !enLogin) return '/login';
      if (autenticado  &&  enLogin) return '/camaras';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (_, __) => const PantallaLogin()),
      ShellRoute(
        builder: (context, state, child) => DisenoGuardia(child: child),
        routes: [
          GoRoute(path: '/camaras', builder: (_, __) => const PantallaCamaras()),
          GoRoute(path: '/eventos', builder: (_, __) => const PantallaEventos()),
        ],
      ),
    ],
  );
});
