-- ============================================================
-- SIVIC DB — Sistema de Visión con IA para Condominios (SaaS)
-- Ejecutar en Supabase SQL Editor
-- ============================================================

-- Limpiar schema público (elimina todas las tablas existentes)
DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END;
$$;

-- ============================================================
-- 1. USUARIOS Y ROLES
-- ============================================================
CREATE TABLE usuarios (
    usuario_id    SERIAL PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    email         VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol           VARCHAR(20) NOT NULL CHECK (rol IN ('admin', 'guardia')),
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 2. ESTRUCTURA SAAS
-- ============================================================
CREATE TABLE planes (
    plan_id         SERIAL PRIMARY KEY,
    nombre          VARCHAR(20) UNIQUE NOT NULL,  -- Basico | Pro | Premium
    precio_mensual  DECIMAL(10,2) NOT NULL
);

CREATE TABLE condominio (
    condominio_id SERIAL PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    ubicacion     TEXT
);

CREATE TABLE suscripciones (
    suscripcion_id SERIAL PRIMARY KEY,
    condominio_id  INT NOT NULL REFERENCES condominio(condominio_id) ON DELETE CASCADE,
    plan_id        INT NOT NULL REFERENCES planes(plan_id),
    fecha_inicio   DATE DEFAULT CURRENT_DATE,
    is_activo      BOOLEAN DEFAULT TRUE
);

CREATE TABLE plan_funcionalidades (
    plan_id        INT NOT NULL REFERENCES planes(plan_id) ON DELETE CASCADE,
    funcionalidad  VARCHAR(50) NOT NULL,  -- detectar_parqueo | detectar_mascotas | generar_reportes
    PRIMARY KEY (plan_id, funcionalidad)
);

-- ============================================================
-- 3. INFRAESTRUCTURA DE CÁMARAS
-- ============================================================
CREATE TABLE camaras (
    camara_id        SERIAL PRIMARY KEY,
    condominio_id    INT NOT NULL REFERENCES condominio(condominio_id) ON DELETE CASCADE,
    nombre_ubicacion VARCHAR(100) NOT NULL,
    rtsp_url         TEXT NOT NULL,
    is_active        BOOLEAN DEFAULT TRUE
);

CREATE TABLE zonas_roi (
    roi_id                SERIAL PRIMARY KEY,
    camara_id             INT NOT NULL REFERENCES camaras(camara_id) ON DELETE CASCADE,
    poligono_coordenadas  JSONB NOT NULL,
    tipo_zona             VARCHAR(50) NOT NULL CHECK (tipo_zona IN ('parqueo', 'jardin', 'area_comun'))
);

-- ============================================================
-- 4. REGLAS DE INFRACCIÓN
-- ============================================================
CREATE TABLE reglas_infraccion (
    regla_id    SERIAL PRIMARY KEY,
    nombre_regla VARCHAR(50) UNIQUE NOT NULL,
    descripcion  TEXT
);

-- ============================================================
-- 5. EVENTOS (detecciones IA)
-- ============================================================
CREATE TABLE eventos (
    evento_id            SERIAL PRIMARY KEY,
    camara_id            INT REFERENCES camaras(camara_id),
    regla_id             INT REFERENCES reglas_infraccion(regla_id),
    timestamp_deteccion  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    confianza_ia         FLOAT NOT NULL CHECK (confianza_ia >= 0 AND confianza_ia <= 1),
    estado               VARCHAR(20) DEFAULT 'pendiente'
                             CHECK (estado IN ('pendiente','en_atencion','resuelto','falsa_alarma')),
    imagen_evidencia_path TEXT,
    resolucion           TEXT,
    atendido_por         INT REFERENCES usuarios(usuario_id),
    tiempo_respuesta     INTERVAL
);

-- ============================================================
-- 6. AUDITORÍA
-- ============================================================
CREATE TABLE logs_auditoria (
    log_id           SERIAL PRIMARY KEY,
    usuario_id       INT REFERENCES usuarios(usuario_id),
    accion           TEXT NOT NULL,
    tabla_afectada   VARCHAR(50),
    timestamp_accion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 7. DATASETS PARA RE-ENTRENAMIENTO IA
-- ============================================================
CREATE TABLE datasets (
    dataset_id     SERIAL PRIMARY KEY,
    nombre         VARCHAR(50) NOT NULL,
    version_modelo VARCHAR(20) NOT NULL
);

CREATE TABLE dataset_eventos (
    dataset_id      INT NOT NULL REFERENCES datasets(dataset_id) ON DELETE CASCADE,
    evento_id       INT NOT NULL REFERENCES eventos(evento_id) ON DELETE CASCADE,
    etiqueta_correcta VARCHAR(50),
    PRIMARY KEY (dataset_id, evento_id)
);

-- ============================================================
-- 6. NOTIFICACIONES (historial de alertas enviadas)
-- ============================================================
CREATE TABLE notificaciones (
    notificacion_id SERIAL PRIMARY KEY,
    evento_id       INT REFERENCES eventos(evento_id) ON DELETE SET NULL,
    usuario_id      INT NOT NULL REFERENCES usuarios(usuario_id) ON DELETE CASCADE,
    titulo          TEXT NOT NULL,
    cuerpo          TEXT,
    token_fcm       TEXT,
    estado          VARCHAR(20) DEFAULT 'enviada'
                        CHECK (estado IN ('enviada', 'leida', 'fallida')),
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================
-- 6. ÍNDICES
-- ============================================================
CREATE INDEX idx_notificaciones_usuario ON notificaciones(usuario_id);
CREATE INDEX idx_notificaciones_evento  ON notificaciones(evento_id);
CREATE INDEX idx_notificaciones_estado  ON notificaciones(estado);
CREATE INDEX idx_eventos_camara      ON eventos(camara_id);
CREATE INDEX idx_eventos_timestamp   ON eventos(timestamp_deteccion DESC);
CREATE INDEX idx_eventos_estado      ON eventos(estado) WHERE estado = 'pendiente';
CREATE INDEX idx_eventos_atendido_por ON eventos(atendido_por);
CREATE INDEX idx_eventos_regla       ON eventos(regla_id);
CREATE INDEX idx_suscripciones_activas ON suscripciones(condominio_id, is_activo) WHERE is_activo = TRUE;
CREATE INDEX idx_camaras_condominio  ON camaras(condominio_id) WHERE is_active = TRUE;
CREATE INDEX idx_zonas_roi_camara    ON zonas_roi(camara_id);
CREATE INDEX idx_logs_usuario        ON logs_auditoria(usuario_id);
CREATE INDEX idx_logs_timestamp      ON logs_auditoria(timestamp_accion DESC);
CREATE INDEX idx_usuarios_rol        ON usuarios(rol);

-- ============================================================
-- 7. TRIGGERS
-- ============================================================

-- Calcula tiempo de respuesta al atender un evento
CREATE OR REPLACE FUNCTION calcular_tiempo_respuesta()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.estado IN ('en_atencion', 'resuelto')
       AND OLD.estado = 'pendiente'
       AND NEW.tiempo_respuesta IS NULL THEN
        NEW.tiempo_respuesta = CURRENT_TIMESTAMP - NEW.timestamp_deteccion;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_tiempo_respuesta
BEFORE UPDATE OF estado ON eventos
FOR EACH ROW EXECUTE FUNCTION calcular_tiempo_respuesta();

-- Log automático de cambios de estado en eventos
CREATE OR REPLACE FUNCTION log_cambios_eventos()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.estado IS DISTINCT FROM NEW.estado THEN
        INSERT INTO logs_auditoria (usuario_id, accion, tabla_afectada)
        VALUES (
            NEW.atendido_por,
            'Evento ' || NEW.evento_id || ': ' || COALESCE(OLD.estado, 'NULL') || ' -> ' || NEW.estado,
            'eventos'
        );
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_log_eventos
AFTER UPDATE OF estado ON eventos
FOR EACH ROW EXECUTE FUNCTION log_cambios_eventos();

-- Control de suscripciones: Basico/Pro expiran a los 30 días
CREATE OR REPLACE FUNCTION actualizar_estado_suscripcion()
RETURNS TRIGGER AS $$
DECLARE plan_nombre VARCHAR(20);
BEGIN
    SELECT nombre INTO plan_nombre FROM planes WHERE plan_id = NEW.plan_id;
    IF plan_nombre IN ('Basico', 'Pro') AND NEW.fecha_inicio < CURRENT_DATE - INTERVAL '30 days' THEN
        NEW.is_activo = FALSE;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_control_suscripcion
BEFORE INSERT OR UPDATE OF fecha_inicio, plan_id ON suscripciones
FOR EACH ROW EXECUTE FUNCTION actualizar_estado_suscripcion();

-- ============================================================
-- 8. DATOS INICIALES
-- ============================================================
INSERT INTO planes (nombre, precio_mensual) VALUES
('Basico',   49.99),
('Pro',      99.99),
('Premium', 199.99);

INSERT INTO reglas_infraccion (nombre_regla, descripcion) VALUES
('bloqueo_vehicular',    'Vehículo estacionado en zona prohibida'),
('mascota_suelta',       'Mascota sin correa en áreas comunes'),
('acceso_no_autorizado', 'Persona ingresando sin autorización'),
('exceso_velocidad',     'Vehículo superando límite de velocidad interno');

INSERT INTO plan_funcionalidades (plan_id, funcionalidad) VALUES
((SELECT plan_id FROM planes WHERE nombre = 'Basico'),   'detectar_parqueo'),
((SELECT plan_id FROM planes WHERE nombre = 'Pro'),      'detectar_parqueo'),
((SELECT plan_id FROM planes WHERE nombre = 'Pro'),      'detectar_mascotas'),
((SELECT plan_id FROM planes WHERE nombre = 'Premium'),  'detectar_parqueo'),
((SELECT plan_id FROM planes WHERE nombre = 'Premium'),  'detectar_mascotas'),
((SELECT plan_id FROM planes WHERE nombre = 'Premium'),  'generar_reportes');
