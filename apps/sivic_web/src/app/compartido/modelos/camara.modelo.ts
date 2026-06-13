export interface Camara {
  camara_id: number;
  condominio_id: number;
  nombre: string;
  ubicacion: string;
  tipo_stream: 'mjpeg' | 'hls' | 'archivo';
  url_stream: string;
  activa: boolean;
  created_at?: string;
}
