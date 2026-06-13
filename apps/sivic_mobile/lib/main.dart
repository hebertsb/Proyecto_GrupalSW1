import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'nucleo/temas/tema.dart';
import 'nucleo/proveedores/tema_proveedor.dart';
import 'nucleo/proveedores/auth_proveedor.dart';
import 'nucleo/rutas/rutas_app.dart';

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const ProviderScope(child: AppSivic()));
}

class AppSivic extends ConsumerWidget {
  const AppSivic({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final modoTema = ref.watch(temaProvider);
    final router   = ref.watch(routerProvider);

    // Carga sesión guardada al iniciar
    ref.read(authProvider.notifier).cargarSesionGuardada();

    return MaterialApp.router(
      title: 'SIVIC Guardia',
      debugShowCheckedModeBanner: false,
      themeMode:   modoTema,
      theme:       temaClaro(),
      darkTheme:   temaOscuro(),
      routerConfig: router,
    );
  }
}
