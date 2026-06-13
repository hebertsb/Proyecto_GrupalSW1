import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import '../../nucleo/constantes/colores.dart';

class DisenoGuardia extends StatelessWidget {
  final Widget child;
  const DisenoGuardia({super.key, required this.child});

  int _indiceActual(BuildContext context) {
    final location = GoRouterState.of(context).matchedLocation;
    if (location.startsWith('/camaras')) return 0;
    if (location.startsWith('/eventos')) return 1;
    return 0;
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: child,
      bottomNavigationBar: NavigationBar(
        backgroundColor: kSuperficieOscura,
        indicatorColor: kPrimario.withAlpha(50),
        selectedIndex: _indiceActual(context),
        onDestinationSelected: (i) {
          switch (i) {
            case 0: context.go('/camaras'); break;
            case 1: context.go('/eventos'); break;
          }
        },
        destinations: const [
          NavigationDestination(
            icon: Icon(Icons.videocam_outlined, color: kTexto2Oscuro),
            selectedIcon: Icon(Icons.videocam, color: kPrimario),
            label: 'Cámaras',
          ),
          NavigationDestination(
            icon: Icon(Icons.notifications_outlined, color: kTexto2Oscuro),
            selectedIcon: Icon(Icons.notifications, color: kPrimario),
            label: 'Eventos',
          ),
        ],
      ),
    );
  }
}
