import { Component, OnInit, signal } from '@angular/core';
import { NgClass, DatePipe } from '@angular/common';
import { EventosServicio } from '../../../compartido/servicios/eventos.servicio';
import { Evento, EstadoEvento } from '../../../compartido/modelos/evento.modelo';
import { CabeceraComponent } from '../../../compartido/componentes/cabecera/cabecera.component';

@Component({
  selector: 'app-lista-eventos',
  standalone: true,
  imports: [NgClass, DatePipe, CabeceraComponent],
  templateUrl: './lista-eventos.component.html',
  styleUrl: './lista-eventos.component.scss',
})
export class ListaEventosComponent implements OnInit {
  readonly eventos  = signal<Evento[]>([]);
  readonly cargando = signal(true);
  readonly filtro   = signal<EstadoEvento | ''>('');

  readonly estados: { valor: EstadoEvento | ''; etiqueta: string }[] = [
    { valor: '',             etiqueta: 'Todos' },
    { valor: 'pendiente',    etiqueta: 'Pendiente' },
    { valor: 'en_atencion',  etiqueta: 'En Atención' },
    { valor: 'resuelto',     etiqueta: 'Resuelto' },
    { valor: 'falsa_alarma', etiqueta: 'Falsa Alarma' },
  ];

  constructor(private eventosSrv: EventosServicio) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.cargando.set(true);
    const params = this.filtro() ? { estado: this.filtro() as EstadoEvento } : undefined;
    this.eventosSrv.listar(params).subscribe({
      next:  lista => { this.eventos.set(lista); this.cargando.set(false); },
      error: ()    => this.cargando.set(false),
    });
  }

  cambiarFiltro(estado: EstadoEvento | '') {
    this.filtro.set(estado);
    this.cargar();
  }

  actualizarEstado(evento: Evento, estado: EstadoEvento) {
    this.eventosSrv.actualizarEstado(evento.evento_id, estado).subscribe(() => this.cargar());
  }

  claseEstado(estado: string): string {
    const mapa: Record<string, string> = {
      pendiente:    'estado--pendiente',
      en_atencion:  'estado--revision',
      resuelto:     'estado--resuelto',
      falsa_alarma: 'estado--falso',
    };
    return mapa[estado] ?? '';
  }
}
