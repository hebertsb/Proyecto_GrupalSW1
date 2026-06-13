import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../nucleo/constantes/colores.dart';
import '../../nucleo/proveedores/auth_proveedor.dart';

class PantallaLogin extends ConsumerStatefulWidget {
  const PantallaLogin({super.key});

  @override
  ConsumerState<PantallaLogin> createState() => _PantallaLoginState();
}

class _PantallaLoginState extends ConsumerState<PantallaLogin> {
  final _formKey  = GlobalKey<FormState>();
  final _email    = TextEditingController();
  final _password = TextEditingController();

  Future<void> _enviar() async {
    if (!_formKey.currentState!.validate()) return;
    final ok = await ref.read(authProvider.notifier).iniciarSesion(
      _email.text.trim(),
      _password.text,
    );
    if (ok && mounted) context.go('/camaras');
  }

  @override
  void dispose() {
    _email.dispose();
    _password.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final estado = ref.watch(authProvider);

    return Scaffold(
      backgroundColor: kFondoOscuro,
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 380),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                const Icon(Icons.security, size: 64, color: kPrimario),
                const SizedBox(height: 12),
                Text('SIVIC', style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700)),
                const SizedBox(height: 4),
                Text('Sistema de Vigilancia Inteligente', style: Theme.of(context).textTheme.bodySmall),
                const SizedBox(height: 36),

                if (estado.error != null)
                  Container(
                    width: double.infinity,
                    margin: const EdgeInsets.only(bottom: 16),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: kPeligro.withAlpha(30),
                      border: Border.all(color: kPeligro),
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: Text(estado.error!, style: const TextStyle(color: kPeligro, fontSize: 13)),
                  ),

                Form(
                  key: _formKey,
                  child: Column(
                    children: [
                      _CampoTexto(
                        controlador: _email,
                        etiqueta: 'Correo electrónico',
                        icono: Icons.email_outlined,
                        teclado: TextInputType.emailAddress,
                        validador: (v) => (v == null || !v.contains('@')) ? 'Email inválido' : null,
                      ),
                      const SizedBox(height: 16),
                      _CampoTexto(
                        controlador: _password,
                        etiqueta: 'Contraseña',
                        icono: Icons.lock_outline,
                        esPassword: true,
                        validador: (v) => (v == null || v.isEmpty) ? 'Requerido' : null,
                      ),
                      const SizedBox(height: 24),
                      SizedBox(
                        width: double.infinity,
                        height: 48,
                        child: FilledButton(
                          onPressed: estado.cargando ? null : _enviar,
                          style: FilledButton.styleFrom(backgroundColor: kPrimario),
                          child: estado.cargando
                              ? const SizedBox(width: 20, height: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                              : const Text('Ingresar', style: TextStyle(fontSize: 15, fontWeight: FontWeight.w600)),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _CampoTexto extends StatefulWidget {
  final TextEditingController controlador;
  final String etiqueta;
  final IconData icono;
  final bool esPassword;
  final TextInputType teclado;
  final String? Function(String?)? validador;

  const _CampoTexto({
    required this.controlador,
    required this.etiqueta,
    required this.icono,
    this.esPassword = false,
    this.teclado = TextInputType.text,
    this.validador,
  });

  @override
  State<_CampoTexto> createState() => _CampoTextoState();
}

class _CampoTextoState extends State<_CampoTexto> {
  bool _oculto = true;

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: widget.controlador,
      keyboardType: widget.teclado,
      obscureText: widget.esPassword && _oculto,
      validator: widget.validador,
      style: const TextStyle(color: kTextoOscuro),
      decoration: InputDecoration(
        labelText: widget.etiqueta,
        prefixIcon: Icon(widget.icono, color: kTexto2Oscuro),
        suffixIcon: widget.esPassword
            ? IconButton(
                icon: Icon(_oculto ? Icons.visibility_off : Icons.visibility, color: kTexto2Oscuro),
                onPressed: () => setState(() => _oculto = !_oculto),
              )
            : null,
        filled: true,
        fillColor: kSuperficie2Oscura,
        border: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: kBordeOscuro)),
        enabledBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: BorderSide(color: kBordeOscuro)),
        focusedBorder: OutlineInputBorder(borderRadius: BorderRadius.circular(8), borderSide: const BorderSide(color: kPrimario)),
      ),
    );
  }
}
