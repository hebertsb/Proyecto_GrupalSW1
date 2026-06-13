import { Component, OnInit, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { FormsModule } from '@angular/forms';
import { entorno } from '../../../../environments/environment';
import { CabeceraComponent } from '../../../compartido/componentes/cabecera/cabecera.component';

interface ReglaInfraccion {
  regla_id:   number;
  nombre:     string;
  descripcion?: string;
  umbral_confianza: number;
  activa:     boolean;
}

@Component({
  selector: 'app-gestion-reglas',
  standalone: true,
  imports: [FormsModule, CabeceraComponent],
  templateUrl: './gestion-reglas.component.html',
  styleUrl: './gestion-reglas.component.scss',
})
export class GestionReglasComponent implements OnInit {
  readonly reglas   = signal<ReglaInfraccion[]>([]);
  readonly cargando = signal(true);

  constructor(private http: HttpClient) {}

  ngOnInit() { this.cargar(); }

  cargar() {
    this.http.get<ReglaInfraccion[]>(`${entorno.apiUrl}/reglas/`).subscribe({
      next:  lista => { this.reglas.set(lista); this.cargando.set(false); },
      error: ()    => this.cargando.set(false),
    });
  }

  alternarActiva(regla: ReglaInfraccion) {
    this.http.patch(`${entorno.apiUrl}/reglas/${regla.regla_id}/`, { activa: !regla.activa })
      .subscribe(() => this.cargar());
  }
}
