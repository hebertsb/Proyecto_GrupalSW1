class Evento {
  final int    eventoId;
  final int    camaraId;
  final int    reglaId;
  final double confianza;
  final String estado;
  final String? imagenPath;
  final String  creadoEn;
  final String? camaraNombre;
  final String? reglaNombre;

  const Evento({
    required this.eventoId,
    required this.camaraId,
    required this.reglaId,
    required this.confianza,
    required this.estado,
    this.imagenPath,
    required this.creadoEn,
    this.camaraNombre,
    this.reglaNombre,
  });

  factory Evento.fromJson(Map<String, dynamic> json) => Evento(
    eventoId:    json['evento_id'] as int,
    camaraId:    json['camara_id'] as int,
    reglaId:     json['regla_id'] as int,
    confianza:   (json['confianza'] as num).toDouble(),
    estado:      json['estado'] as String,
    imagenPath:  json['imagen_path'] as String?,
    creadoEn:    json['created_at'] as String,
    camaraNombre: json['camara_nombre'] as String?,
    reglaNombre:  json['regla_nombre'] as String?,
  );
}
