class Evento {
  final int    eventoId;
  final int    camaraId;
  final int    reglaId;
  final double confianzaIa;
  final String estado;
  final String? imagenEvidenciaPath;
  final String  timestampDeteccion;
  final String? camaraNombre;
  final String? reglaNombre;

  const Evento({
    required this.eventoId,
    required this.camaraId,
    required this.reglaId,
    required this.confianzaIa,
    required this.estado,
    this.imagenEvidenciaPath,
    required this.timestampDeteccion,
    this.camaraNombre,
    this.reglaNombre,
  });

  factory Evento.fromJson(Map<String, dynamic> json) => Evento(
    eventoId:             json['evento_id'] as int,
    camaraId:             json['camara_id'] as int,
    reglaId:              json['regla_id'] as int,
    confianzaIa:          (json['confianza_ia'] as num).toDouble(),
    estado:               json['estado'] as String,
    imagenEvidenciaPath:  json['imagen_evidencia_path'] as String?,
    timestampDeteccion:   json['timestamp_deteccion'] as String,
    camaraNombre:         json['camara_nombre'] as String?,
    reglaNombre:          json['regla_nombre'] as String?,
  );
}
