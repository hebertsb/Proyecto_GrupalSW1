class Camara {
  final int    camaraId;
  final String nombreUbicacion;
  final String rtspUrl;
  final bool   isActive;

  const Camara({
    required this.camaraId,
    required this.nombreUbicacion,
    required this.rtspUrl,
    required this.isActive,
  });

  factory Camara.fromJson(Map<String, dynamic> json) => Camara(
    camaraId:        json['camara_id'] as int,
    nombreUbicacion: json['nombre_ubicacion'] as String,
    rtspUrl:         json['rtsp_url'] as String,
    isActive:        json['is_active'] as bool,
  );
}
