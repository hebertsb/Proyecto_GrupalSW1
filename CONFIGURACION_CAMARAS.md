# Guía: Conectar cámaras de celular al sistema SIVIC

Esta guía explica cómo enlazar la cámara de un celular (Android) como una
cámara real del panel **Cámaras**, para que el sistema reciba video en vivo
y la IA pueda analizarlo.

---

## 1. Requisitos

- El celular y la computadora donde corre el backend de Django **deben
  estar en la misma red WiFi**.
- App de cámara IP instalada en el celular (ver opción recomendada abajo).
- Backend corriendo (`python manage.py runserver`) y frontend Angular
  corriendo (`ng serve`).

---

## 2. App recomendada para el celular: **IP Webcam**

Busca en Play Store: **"IP Webcam"** (autor: Pavel Khlebovich).

Es más estable que otras apps tipo "Visor de cámara IP WiFi": usa HTTP/MJPEG
(no se corta la conexión), permite configurar resolución, calidad, zoom,
enfoque, y puede correr en segundo plano.

**Pasos en el celular:**

1. Abre la app.
2. (Opcional) En **Ajustes → Preferencias de video**, ajusta resolución,
   calidad y zoom a gusto.
3. (Opcional) En **Ajustes → Permisos adicionales**, activa que la app
   corra en segundo plano (para que no se corte si bloqueas la pantalla).
4. Baja hasta el final y toca **"Iniciar servidor"**.
5. La app mostrará algo como:

   ```
   IPv4: http://192.168.1.X:8080
   ```

   Esa es la IP y puerto que vas a usar. **Anótala.**
   Configura así en el panel (/configuracion/camaras, editar "camara celular 1" o cualquiera de las otras 3):

6. Protocolo: http
7. IP / Host: 192.168.1.8
8. Puerto: 8080
9. Usuario / Contraseña: vacío (dice "no establecido")
10. Ruta: /video
11. URL final: http://192.168.1.8:8080/video

Luego Probar conexión → Guardar.

> Mientras pruebas, deja la app abierta con la vista de cámara activa.
> Si la cierras o bloqueas el celular (sin el permiso de segundo plano),
> el stream se corta y la cámara dejará de transmitir.

### Alternativa: apps con RTSP (ej. "Visor de cámara IP WiFi")

Algunas apps muestran un dato tipo:

```
rtsp://192.168.1.X:8556
Usuario: admin
Contraseña: xxxxxx
```

Esto también funciona (ver sección 3, modo RTSP), pero suelen ser menos
estables y no permiten ajustar zoom/resolución.

---

## 3. Configurar la cámara en el panel SIVIC

1. Inicia sesión como **Admin**.
2. En el menú lateral, entra a **"Config. Cámaras"** (`/configuracion/camaras`).
3. Elige una cámara existente y dale click al ícono ✏️ **Editar** (o
   "Nueva cámara" si quieres agregar una).
4. En el modal, asegúrate de que el modo esté en **"Asistido"**.

### Si usaste IP Webcam (HTTP):

| Campo           | Valor                                |
| --------------- | ------------------------------------ |
| Protocolo       | `http`                               |
| IP / Host       | `192.168.1.X` (la que mostró la app) |
| Puerto          | `8080`                               |
| Usuario         | (vacío)                              |
| Contraseña      | (vacío)                              |
| Ruta del stream | `/video`                             |

URL final esperada: `http://192.168.1.X:8080/video`

### Si usaste una app con RTSP:

| Campo           | Valor                                    |
| --------------- | ---------------------------------------- |
| Protocolo       | `rtsp`                                   |
| IP / Host       | la IP que indica la app                  |
| Puerto          | el puerto que indica la app (ej. `8556`) |
| Usuario         | usuario indicado (ej. `admin`)           |
| Contraseña      | contraseña indicada                      |
| Ruta del stream | `/` (probar primero con esto)            |

URL final esperada: `rtsp://usuario:contraseña@192.168.1.X:8556/`

---

## 4. Probar conexión y guardar

1. Click en **"Probar conexión"**.
   - ✅ **"Conexión exitosa"** → todo bien, continúa.
   - ❌ Error → revisa:
     - Que el celular y la PC estén en la **misma red WiFi**.
     - Que la app de cámara siga abierta y transmitiendo.
     - Que la IP no haya cambiado (las apps suelen mostrarla en pantalla,
       puede variar si el celular se reconecta al WiFi).
2. Asegúrate de llenar el campo **"Nombre / Ubicación"** (obligatorio).
3. Click en **"Guardar cámara"**.

---

## 5. Ver el video en vivo

1. Ve al panel principal **"Cámaras"** (`/camaras`).
2. La celda de esa cámara debe mostrar el video en vivo con el badge
   **LIVE** parpadeando.
3. Tanto el rol **Admin** como **Guardia** pueden ver el mismo stream.

---

## 6. Modo alternativo: arrastrar video o imagen (sin conexión WiFi)

Si una cámara no tiene conexión (no hay celular disponible en ese
momento), se puede simular su feed arrastrando un archivo:

1. En el panel **"Cámaras"** (`/camaras`), arrastra un video o imagen
   directo sobre la celda de la cámara deseada.
2. El archivo se reproduce/muestra localmente en esa celda.
3. La IA analiza el contenido (imágenes al instante, videos cada ~2
   segundos) igual que si fuera una transmisión en vivo.
4. Para volver al modo en vivo, usa el botón de "volver" en la esquina
   de la celda.

---

## 7. Detección con IA (modelo entrenado)

Por defecto, el sistema funciona sin modelo de IA (no detecta nada, pero
todo el flujo de video/streaming/drag&drop funciona normalmente).

Para activar la detección real:

1. Coloca el archivo del modelo entrenado (`.pt`) en el servidor backend.
2. En `apps/sivic_backend/.env`, agrega:
   ```
   YOLO_MODEL_PATH=ruta/al/modelo/best.pt
   ```
3. Reinicia el backend (`python manage.py runserver`).
4. A partir de ese momento, tanto el video en vivo como los archivos
   arrastrados mostrarán los recuadros de detección (bounding boxes)
   sobre el video.

---

## 8. Resumen rápido

```
Celular: instalar "IP Webcam" → Iniciar servidor → anotar IP:puerto
Panel:   Config. Cámaras → Editar cámara → Asistido
         Protocolo=http, Host=<IP del celular>, Puerto=8080, Ruta=/video
         → Probar conexión → Guardar
Ver:     Panel "Cámaras" → la celda muestra video en vivo (badge LIVE)
```
