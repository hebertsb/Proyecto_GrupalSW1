import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../nucleo/constantes/colores.dart';
import '../../nucleo/proveedores/eventos_proveedor.dart';
import '../../nucleo/proveedores/auth_proveedor.dart';
import '../../compartido/modelos/evento.modelo.dart';

class PantallaEventos extends ConsumerStatefulWidget {
  const PantallaEventos({super.key});

  @override
  ConsumerState<PantallaEventos> createState() => _PantallaEventosState();
}

class _PantallaEventosState extends ConsumerState<PantallaEventos> {
  String? _filtro;

  static const _filtros = [
    {'valor': null,              'etiqueta': 'Todos'},
    {'valor': 'pendiente',       'etiqueta': 'Pendiente'},
    {'valor': 'en_revision',     'etiqueta': 'En revisión'},
    {'valor': 'resuelto',        'etiqueta': 'Resuelto'},
    {'valor': 'falso_positivo',  'etiqueta': 'Falso+'},
  ];

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(eventosProvider(_filtro));

    return Scaffold(
      backgroundColor: kFondoOscuro,
      appBar: AppBar(title: const Text('Eventos')),
      body: Column(
        children: [
          // Filtros
          SizedBox(
            height: 44,
            child: ListView.separated(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
              separatorBuilder: (_, __) => const SizedBox(width: 6),
              itemCount: _filtros.length,
              itemBuilder: (_, i) {
                final f = _filtros[i];
                final activo = _filtro == f['valor'];
                return GestureDetector(
                  onTap: () => setState(() => _filtro = f['valor'] as String?),
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                    decoration: BoxDecoration(
                      color: activo ? kPrimario : Colors.transparent,
                      border: Border.all(color: activo ? kPrimario : kBordeOscuro),
                      borderRadius: BorderRadius.circular(20),
                    ),
                    child: Text(f['etiqueta'] as String,
                      style: TextStyle(fontSize: 12, fontWeight: FontWeight.w500,
                        color: activo ? Colors.white : kTexto2Oscuro)),
                  ),
                );
              },
            ),
          ),
          const Divider(height: 1, color: kBordeOscuro),

          // Lista de eventos
          Expanded(
            child: async.when(
              loading: () => const Center(child: CircularProgressIndicator(color: kPrimario)),
              error:   (e, _) => Center(child: Text('Error: $e', style: const TextStyle(color: kPeligro))),
              data: (eventos) => eventos.isEmpty
                ? const Center(child: Column(mainAxisSize: MainAxisSize.min, children: [
                    Icon(Icons.notifications_none, size: 48, color: kBordeOscuro),
                    SizedBox(height: 8),
                    Text('Sin eventos', style: TextStyle(color: kTexto2Oscuro)),
                  ]))
                : RefreshIndicator(
                    color: kPrimario,
                    onRefresh: () async => ref.invalidate(eventosProvider),
                    child: ListView.builder(
                      padding: const EdgeInsets.all(8),
                      itemCount: eventos.length,
                      itemBuilder: (_, i) => _TarjetaEvento(evento: eventos[i], onActualizar: () => ref.invalidate(eventosProvider)),
                    ),
                  ),
            ),
          ),
        ],
      ),
    );
  }
}

class _TarjetaEvento extends ConsumerWidget {
  final Evento evento;
  final VoidCallback onActualizar;
  const _TarjetaEvento({required this.evento, required this.onActualizar});

  Color _colorEstado(String estado) => switch (estado) {
    'pendiente'      => kAdvertencia,
    'en_revision'    => kPrimario,
    'resuelto'       => kExito,
    'falso_positivo' => kTexto2Oscuro,
    _                => kTexto2Oscuro,
  };

  Future<void> _cambiarEstado(BuildContext ctx, WidgetRef ref, String nuevoEstado) async {
    final http = ref.read(httpProvider);
    await http.patch('/eventos/${evento.eventoId}/estado/', data: {'estado': nuevoEstado});
    onActualizar();
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final color = _colorEstado(evento.estado);

    return Card(
      color: kSuperficieOscura,
      margin: const EdgeInsets.only(bottom: 8),
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: BorderSide(color: kBordeOscuro),
      ),
      child: Padding(
        padding: const EdgeInsets.all(12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.notification_important, color: color, size: 18),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(evento.camaraNombre ?? 'Cám. ${evento.camaraId}',
                    style: const TextStyle(fontWeight: FontWeight.w600, color: kTextoOscuro)),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                  decoration: BoxDecoration(
                    border: Border.all(color: color),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Text(evento.estado.replaceAll('_', ' '),
                    style: TextStyle(fontSize: 10, fontWeight: FontWeight.w700, color: color)),
                ),
              ],
            ),
            const SizedBox(height: 6),
            Row(
              children: [
                Text('Regla: ${evento.reglaNombre ?? evento.reglaId}',
                  style: const TextStyle(fontSize: 12, color: kTexto2Oscuro)),
                const Spacer(),
                Text('${(evento.confianza * 100).toStringAsFixed(0)}% confianza',
                  style: TextStyle(fontSize: 12, color: evento.confianza >= 0.8 ? kPeligro : kTexto2Oscuro,
                    fontWeight: FontWeight.w700)),
              ],
            ),
            const SizedBox(height: 4),
            Text(evento.creadoEn.substring(0, 16).replaceFirst('T', ' '),
              style: const TextStyle(fontSize: 11, color: kTexto2Oscuro)),

            if (evento.estado == 'pendiente') ...[
              const SizedBox(height: 10),
              Row(
                mainAxisAlignment: MainAxisAlignment.end,
                children: [
                  _BotonAccion(icono: Icons.search,        etiqueta: 'Revisar',  color: kPrimario,
                    onTap: () => _cambiarEstado(context, ref, 'en_revision')),
                  const SizedBox(width: 8),
                  _BotonAccion(icono: Icons.check_circle,  etiqueta: 'Resolver', color: kExito,
                    onTap: () => _cambiarEstado(context, ref, 'resuelto')),
                  const SizedBox(width: 8),
                  _BotonAccion(icono: Icons.cancel,        etiqueta: 'Falso+',  color: kTexto2Oscuro,
                    onTap: () => _cambiarEstado(context, ref, 'falso_positivo')),
                ],
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class _BotonAccion extends StatelessWidget {
  final IconData icono;
  final String etiqueta;
  final Color color;
  final VoidCallback onTap;
  const _BotonAccion({required this.icono, required this.etiqueta, required this.color, required this.onTap});

  @override
  Widget build(BuildContext context) => TextButton.icon(
    onPressed: onTap,
    icon: Icon(icono, size: 14, color: color),
    label: Text(etiqueta, style: TextStyle(fontSize: 11, color: color)),
    style: TextButton.styleFrom(padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      minimumSize: Size.zero, tapTargetSize: MaterialTapTargetSize.shrinkWrap),
  );
}
