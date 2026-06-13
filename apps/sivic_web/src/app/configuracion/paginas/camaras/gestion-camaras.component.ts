import { Component, OnInit, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { CamarasServicio } from '../../../compartido/servicios/camaras.servicio';
import { Camara } from '../../../compartido/modelos/camara.modelo';
import { CabeceraComponent } from '../../../compartido/componentes/cabecera/cabecera.component';

@Component({
  selector: 'app-gestion-camaras',
  standalone: true,
  imports: [FormsModule, CabeceraComponent],
  templateUrl: './gestion-camaras.component.html',
  styleUrl: './gestion-camaras.component.scss',
})
export class GestionCamarasComponent implements OnInit {
  readonly camaras   = signal<Camara[]>([]);
  readonly cargando  = signal(true);
  readonly modalOpen = signal(false);

  nueva: Partial<Camara> = { is_active: true };

  constructor(private srv: CamarasServicio) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.srv.listar().subscribe({
      next: lista => { this.camaras.set(lista); this.cargando.set(false); },
      error: ()   => this.cargando.set(false),
    });
  }

  guardar() {
    this.srv.crear(this.nueva).subscribe(() => {
      this.modalOpen.set(false);
      this.nueva = { is_active: true };
      this.cargar();
    });
  }

  eliminar(id: number) {
    if (!confirm('¿Eliminar esta cámara?')) return;
    this.srv.eliminar(id).subscribe(() => this.cargar());
  }

  alternarActiva(cam: Camara) {
    this.srv.actualizar(cam.camara_id, { is_active: !cam.is_active }).subscribe(() => this.cargar());
  }
}
