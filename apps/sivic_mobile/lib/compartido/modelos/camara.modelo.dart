class Camara {
  final int    camaraId;
  final String nombre;
  final String ubicacion;
  final String tipoStream;
  final String urlStream;
  final bool   activa;

  const Camara({
    required this.camaraId,
    required this.nombre,
    required this.ubicacion,
    required this.tipoStream,
    required this.urlStream,
    required this.activa,
  });

  factory Camara.fromJson(Map<String, dynamic> json) => Camara(
    camaraId:   json['camara_id'] as int,
    nombre:     json['nombre'] as String,
    ubicacion:  json['ubicacion'] as String,
    tipoStream: json['tipo_stream'] as String,
    urlStream:  json['url_stream'] as String,
    activa:     json['activa'] as bool,
  );
}
