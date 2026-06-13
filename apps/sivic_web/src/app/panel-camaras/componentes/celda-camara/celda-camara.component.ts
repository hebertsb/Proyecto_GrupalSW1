import { Component, Input, OnDestroy, OnInit, signal } from '@angular/core';
import { NgIf, NgClass, DatePipe } from '@angular/common';
import { Camara } from '../../../compartido/modelos/camara.modelo';

@Component({
  selector: 'app-celda-camara',
  standalone: true,
  imports: [NgIf, NgClass, DatePipe],
  templateUrl: './celda-camara.component.html',
  styleUrl: './celda-camara.component.scss',
})
export class CeldaCamaraComponent implements OnInit, OnDestroy {
  @Input({ required: true }) camara!: Camara;
  @Input() seleccionada = false;

  readonly cargando    = signal(true);
  readonly errorStream = signal(false);
  readonly horaActual  = signal(new Date());

  private intervaloReloj?: ReturnType<typeof setInterval>;

  ngOnInit() {
    this.intervaloReloj = setInterval(() => this.horaActual.set(new Date()), 1000);
  }

  ngOnDestroy() {
    clearInterval(this.intervaloReloj);
  }

  alCargar()  { this.cargando.set(false); this.errorStream.set(false); }
  alError()   { this.cargando.set(false); this.errorStream.set(true);  }

  obtenerUrl(): string {
    return this.camara.url_stream;
  }
}
