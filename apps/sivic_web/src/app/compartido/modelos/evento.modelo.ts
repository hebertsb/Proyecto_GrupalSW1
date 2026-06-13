export type EstadoEvento = 'pendiente' | 'en_revision' | 'resuelto' | 'falso_positivo';

export interface Evento {
  evento_id: number;
  camara_id: number;
  regla_id: number;
  confianza: number;
  imagen_path?: string;
  estado: EstadoEvento;
  tiempo_respuesta?: number;
  guardia_id?: number;
  created_at: string;
  camara_nombre?: string;
  regla_nombre?: string;
}
