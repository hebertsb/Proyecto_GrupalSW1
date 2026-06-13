import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:video_player/video_player.dart';
import '../../nucleo/constantes/colores.dart';
import '../../nucleo/proveedores/camaras_proveedor.dart';
import '../../compartido/modelos/camara.modelo.dart';

class PantallaCamaras extends ConsumerStatefulWidget {
  const PantallaCamaras({super.key});

  @override
  ConsumerState<PantallaCamaras> createState() => _PantallaCamarasState();
}

class _PantallaCamarasState extends ConsumerState<PantallaCamaras> {
  int _columnas = 2;
  Camara? _camaraFoco;

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(camarasProvider);

    return Scaffold(
      backgroundColor: kFondoOscuro,
      appBar: AppBar(
        title: const Text('Panel de Cámaras'),
        actions: [
          if (_camaraFoco != null)
            IconButton(icon: const Icon(Icons.close), onPressed: () => setState(() => _camaraFoco = null)),
          _BotonLayout(columnas: 1, actual: _columnas, onTap: () => setState(() { _columnas = 1; _camaraFoco = null; })),
          _BotonLayout(columnas: 2, actual: _columnas, onTap: () => setState(() { _columnas = 2; _camaraFoco = null; })),
          _BotonLayout(columnas: 3, actual: _columnas, onTap: () => setState(() { _columnas = 3; _camaraFoco = null; })),
          const SizedBox(width: 4),
        ],
      ),
      body: async.when(
        loading: () => const Center(child: CircularProgressIndicator(color: kPrimario)),
        error:   (e, _) => Center(child: Text('Error: $e', style: const TextStyle(color: kPeligro))),
        data: (camaras) {
          final lista = _camaraFoco != null ? [_camaraFoco!] : camaras;
          final cols  = _camaraFoco != null ? 1 : _columnas;
          return GridView.builder(
            padding: const EdgeInsets.all(6),
            gridDelegate: SliverGridDelegateWithFixedCrossAxisCount(
              crossAxisCount: cols,
              mainAxisSpacing: 6,
              crossAxisSpacing: 6,
              childAspectRatio: 16 / 9,
            ),
            itemCount: lista.length,
            itemBuilder: (ctx, i) => _CeldaCamara(
              camara: lista[i],
              seleccionada: _camaraFoco?.camaraId == lista[i].camaraId,
              onTap: () => setState(() {
                _camaraFoco = _camaraFoco?.camaraId == lista[i].camaraId ? null : lista[i];
              }),
            ),
          );
        },
      ),
    );
  }
}

class _CeldaCamara extends StatefulWidget {
  final Camara  camara;
  final bool    seleccionada;
  final VoidCallback onTap;
  const _CeldaCamara({required this.camara, required this.seleccionada, required this.onTap});

  @override
  State<_CeldaCamara> createState() => _CeldaCamaraState();
}

class _CeldaCamaraState extends State<_CeldaCamara> {
  VideoPlayerController? _ctrl;
  bool _cargando = true;
  bool _error    = false;

  @override
  void initState() {
    super.initState();
    if (!widget.camara.rtspUrl.contains('/video')) {
      _ctrl = VideoPlayerController.networkUrl(Uri.parse(widget.camara.rtspUrl))
        ..initialize().then((_) {
          _ctrl!.play();
          _ctrl!.setLooping(true);
          if (mounted) setState(() => _cargando = false);
        }).catchError((_) {
          if (mounted) setState(() { _cargando = false; _error = true; });
        });
    } else {
      _cargando = false;
    }
  }

  @override
  void dispose() {
    _ctrl?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: Container(
        decoration: BoxDecoration(
          color: kSuperficieOscura,
          border: Border.all(color: widget.seleccionada ? kPrimario : kBordeOscuro, width: widget.seleccionada ? 2 : 1),
          borderRadius: BorderRadius.circular(8),
        ),
        child: ClipRRect(
          borderRadius: BorderRadius.circular(7),
          child: Stack(
            fit: StackFit.expand,
            children: [
              if (_cargando)
                const Center(child: CircularProgressIndicator(color: kPrimario, strokeWidth: 2))
              else if (_error)
                const Column(mainAxisAlignment: MainAxisAlignment.center, children: [
                  Icon(Icons.videocam_off, color: kPeligro, size: 32),
                  SizedBox(height: 6),
                  Text('Sin señal', style: TextStyle(color: kPeligro, fontSize: 11)),
                ])
              else if (widget.camara.rtspUrl.contains('/video'))
                Image.network(widget.camara.rtspUrl, fit: BoxFit.cover,
                  errorBuilder: (_, __, ___) => const Icon(Icons.videocam_off, color: kPeligro))
              else if (_ctrl != null)
                VideoPlayer(_ctrl!),

              // HUD inferior
              Positioned(
                bottom: 0, left: 0, right: 0,
                child: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 5),
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(begin: Alignment.bottomCenter, end: Alignment.topCenter,
                      colors: [Color(0xBF000000), Colors.transparent]),
                  ),
                  child: Text(widget.camara.nombreUbicacion,
                    style: const TextStyle(color: Colors.white, fontSize: 11, fontWeight: FontWeight.w600)),
                ),
              ),

              // Badge LIVE
              if (!_error && !_cargando)
                Positioned(
                  top: 6, left: 6,
                  child: Container(
                    padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                    decoration: BoxDecoration(color: kPeligro.withAlpha(210), borderRadius: BorderRadius.circular(4)),
                    child: const Text('LIVE', style: TextStyle(color: Colors.white, fontSize: 9, fontWeight: FontWeight.w800)),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _BotonLayout extends StatelessWidget {
  final int columnas, actual;
  final VoidCallback onTap;
  const _BotonLayout({required this.columnas, required this.actual, required this.onTap});

  @override
  Widget build(BuildContext context) {
    final activo = columnas == actual;
    return IconButton(
      onPressed: onTap,
      icon: Icon(
        columnas == 1 ? Icons.crop_square : columnas == 2 ? Icons.grid_view : Icons.apps,
        color: activo ? kPrimario : kTexto2Oscuro,
        size: 20,
      ),
    );
  }
}
