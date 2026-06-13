export type EstadoEvento = 'pendiente' | 'en_atencion' | 'resuelto' | 'falsa_alarma';

export interface Evento {
  evento_id:             number;
  camara_id:             number;
  regla_id:              number;
  confianza_ia:          number;
  imagen_evidencia_path?: string;
  estado:                EstadoEvento;
  tiempo_respuesta?:     string;
  atendido_por?:         number;
  timestamp_deteccion:   string;
  camara_nombre?:        string;
  regla_nombre?:         string;
}
