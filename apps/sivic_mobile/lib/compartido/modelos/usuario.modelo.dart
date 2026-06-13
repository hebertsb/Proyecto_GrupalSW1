class Usuario {
  final int    usuarioId;
  final String nombre;
  final String email;
  final String rol;

  const Usuario({
    required this.usuarioId,
    required this.nombre,
    required this.email,
    required this.rol,
  });

  factory Usuario.fromJson(Map<String, dynamic> json) => Usuario(
    usuarioId: json['usuario_id'] as int,
    nombre:    json['nombre'] as String,
    email:     json['email'] as String,
    rol:       json['rol'] as String,
  );

  bool get esAdmin => rol == 'admin';
}
