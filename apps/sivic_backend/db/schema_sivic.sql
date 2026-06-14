-- ============================================================
-- SIVIC DB — Sistema de Visión con IA para Condominios (SaaS)
-- Ejecutar en Supabase SQL Editor
-- ============================================================

-- Limpiar schema público: tablas y funciones (permite re-ejecutar sin errores)
DO $$
DECLARE r RECORD;
BEGIN
    FOR r IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
        EXECUTE 'DROP TABLE IF EXISTS public.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END;
$$;

DROP FUNCTION IF EXISTS calcular_tiempo_respuesta() CASCADE;
DROP FUNCTION IF EXISTS log_cambios_eventos() CASCADE;
DROP FUNCTION IF EXISTS actualizar_estado_suscripcion() CASCADE;
DROP FUNCTION IF EXISTS sincronizar_activo() CASCADE;

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
    precio_mensual  DECIMAL(10,2) NOT NULL,
    stripe_precio_id VARCHAR(255) UNIQUE          -- price_xxx de Stripe (se rellena tras crear los Prices en el dashboard)
);

CREATE TABLE condominio (
    condominio_id     SERIAL PRIMARY KEY,
    nombre            VARCHAR(100) NOT NULL,
    ubicacion         TEXT,
    stripe_cliente_id  VARCHAR(255) UNIQUE  -- cus_xxx de Stripe (se crea al registrar el condominio)
);

CREATE TABLE suscripciones (
    suscripcion_id          SERIAL PRIMARY KEY,
    condominio_id           INT NOT NULL REFERENCES condominio(condominio_id) ON DELETE CASCADE,
    plan_id                 INT NOT NULL REFERENCES planes(plan_id),
    fecha_inicio            DATE DEFAULT CURRENT_DATE,
    fecha_fin               DATE,                         -- próxima fecha de renovación/vencimiento
    is_activo               BOOLEAN DEFAULT FALSE,   -- FALSE hasta que Stripe confirme el pago
    stripe_suscripcion_id   VARCHAR(255) UNIQUE,          -- sub_xxx de Stripe
    stripe_estado           VARCHAR(20) DEFAULT 'incomplete'
                                CHECK (stripe_estado IN (
                                    'incomplete','incomplete_expired','trialing',
                                    'active','past_due','canceled','unpaid','paused'
                                )),
    periodo_actual_inicio   DATE,                         -- inicio del período de Stripe actual
    periodo_actual_fin      DATE,                         -- fin del período de Stripe actual
    cancelar_al_vencer      BOOLEAN DEFAULT FALSE         -- el usuario pidió cancelar al vencer
);

CREATE TABLE plan_funcionalidades (
    plan_id        INT NOT NULL REFERENCES planes(plan_id) ON DELETE CASCADE,
    funcionalidad  VARCHAR(50) NOT NULL,  -- detectar_parqueo | detectar_mascotas | generar_reportes
    PRIMARY KEY (plan_id, funcionalidad)
);

-- Historial de facturas/cobros de Stripe
CREATE TABLE pagos (
    pago_id                  SERIAL PRIMARY KEY,
    suscripcion_id           INT NOT NULL REFERENCES suscripciones(suscripcion_id) ON DELETE CASCADE,
    condominio_id            INT NOT NULL REFERENCES condominio(condominio_id) ON DELETE CASCADE,
    stripe_factura_id        VARCHAR(255) UNIQUE NOT NULL,  -- in_xxx de Stripe
    stripe_intento_pago_id   VARCHAR(255),                  -- pi_xxx (puede ser NULL en trials)
    monto                    DECIMAL(10,2) NOT NULL,
    moneda                   VARCHAR(3) DEFAULT 'usd',
    estado                   VARCHAR(20) NOT NULL DEFAULT 'open'
                                 CHECK (estado IN ('draft','open','paid','uncollectible','void')),
    periodo_inicio           DATE,
    periodo_fin              DATE,
    creado_en                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    pagado_en                TIMESTAMP
);

-- Registro de webhooks recibidos de Stripe (garantiza idempotencia)
CREATE TABLE eventos_webhook_stripe (
    stripe_evento_id  VARCHAR(255) PRIMARY KEY,  -- evt_xxx de Stripe (PK natural, no SERIAL)
    tipo_evento       VARCHAR(100) NOT NULL,      -- customer.subscription.updated, invoice.paid, …
    procesado_en      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    datos_evento      JSONB                       -- cuerpo completo del evento para auditoría
);

-- Reportes mensuales automáticos (solo plan Premium)
CREATE TABLE reportes_mensuales (
    reporte_id      SERIAL PRIMARY KEY,
    condominio_id   INT NOT NULL REFERENCES condominio(condominio_id) ON DELETE CASCADE,
    periodo         DATE NOT NULL,               -- primer día del mes reportado (ej: 2026-06-01)
    total_eventos   INT DEFAULT 0,
    eventos_parqueo INT DEFAULT 0,
    eventos_mascotas INT DEFAULT 0,
    eventos_acceso  INT DEFAULT 0,
    generado_en     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enviado_en      TIMESTAMP,                   -- cuándo se envió por email al admin
    ruta_pdf        TEXT,                        -- path al PDF generado (S3/Supabase Storage)
    UNIQUE (condominio_id, periodo)
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
    tipo_zona             VARCHAR(50) NOT NULL
    -- CHECK eliminado en prod: ALTER TABLE zonas_roi DROP CONSTRAINT zonas_roi_tipo_zona_check
    -- Valores válidos: zona_prohibida | horario_restringido | perimetro | parqueo | area_comun | jardin
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
-- 8. PLANO INTERACTIVO DEL CONDOMINIO
-- ============================================================
CREATE TABLE planos_condominio (
    plano_id      SERIAL PRIMARY KEY,
    condominio_id INT NOT NULL REFERENCES condominio(condominio_id) ON DELETE CASCADE,
    nombre        VARCHAR(100) NOT NULL,
    imagen_url    TEXT NOT NULL,
    created_at    TIMESTAMP DEFAULT NOW()
);

CREATE TABLE posiciones_camaras (
    posicion_id SERIAL PRIMARY KEY,
    plano_id    INT NOT NULL REFERENCES planos_condominio(plano_id) ON DELETE CASCADE,
    camara_id   INT NOT NULL REFERENCES camaras(camara_id) ON DELETE CASCADE,
    pos_x       DECIMAL(5,4) NOT NULL,
    pos_y       DECIMAL(5,4) NOT NULL,
    UNIQUE(plano_id, camara_id)
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
CREATE INDEX idx_suscripciones_activas    ON suscripciones(condominio_id) WHERE is_activo = TRUE;
CREATE INDEX idx_suscripciones_stripe     ON suscripciones(stripe_suscripcion_id);
CREATE INDEX idx_pagos_suscripcion        ON pagos(suscripcion_id);
CREATE INDEX idx_pagos_condominio         ON pagos(condominio_id);
CREATE INDEX idx_pagos_estado             ON pagos(estado);
CREATE INDEX idx_pagos_creado_en          ON pagos(creado_en DESC);
CREATE INDEX idx_webhook_tipo             ON eventos_webhook_stripe(tipo_evento);
CREATE INDEX idx_webhook_procesado        ON eventos_webhook_stripe(procesado_en DESC);
CREATE INDEX idx_reportes_condominio      ON reportes_mensuales(condominio_id);
CREATE INDEX idx_reportes_periodo         ON reportes_mensuales(periodo DESC);
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

-- Sincroniza is_activo con el estado que reporta Stripe vía webhook.
-- 'active' y 'trialing' son los únicos estados que Stripe considera vigentes.
-- El backend actualiza stripe_estado al recibir customer.subscription.updated
-- y este trigger propaga el cambio a is_activo automáticamente.
CREATE OR REPLACE FUNCTION sincronizar_activo()
RETURNS TRIGGER AS $$
BEGIN
    NEW.is_activo = (NEW.stripe_estado IN ('active', 'trialing'));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sincronizar_activo
BEFORE INSERT OR UPDATE OF stripe_estado ON suscripciones
FOR EACH ROW EXECUTE FUNCTION sincronizar_activo();

-- ============================================================
-- 8. DATOS INICIALES
-- ============================================================
INSERT INTO planes (nombre, precio_mensual) VALUES
('Basico',   49.99),
('Pro',      99.99),
('Premium', 199.99);

INSERT INTO reglas_infraccion (nombre_regla, descripcion) VALUES
('bloqueo_vehicular',      'Vehiculo estacionado en zona prohibida'),
('mascota_suelta',         'Mascota sin correa en areas comunes'),
('acceso_no_autorizado',   'Persona ingresando sin autorizacion'),
('exceso_velocidad',       'Vehiculo superando limite de velocidad interno'),
('persona_zona_restringida','Persona detectada en zona de acceso restringido'),
('merodeo',                'Persona permanece en la misma zona mas de 30 segundos sin razon aparente'),
('vehiculo_no_autorizado', 'Vehiculo detectado en zona restringida o en horario no permitido'),
('personas_peleando',      'Pelea o violencia fisica detectada entre personas'),
('caida_persona',          'Caida de persona detectada en area del condominio'),
('intrusion_nocturna',     'Persona detectada en horario nocturno (22:00-06:00)'),
('acceso_fuera_horario',   'Persona en zona restringida fuera del horario permitido');

INSERT INTO plan_funcionalidades (plan_id, funcionalidad) VALUES
((SELECT plan_id FROM planes WHERE nombre = 'Basico'),   'detectar_parqueo'),
((SELECT plan_id FROM planes WHERE nombre = 'Pro'),      'detectar_parqueo'),
((SELECT plan_id FROM planes WHERE nombre = 'Pro'),      'detectar_mascotas'),
((SELECT plan_id FROM planes WHERE nombre = 'Premium'),  'detectar_parqueo'),
((SELECT plan_id FROM planes WHERE nombre = 'Premium'),  'detectar_mascotas'),
((SELECT plan_id FROM planes WHERE nombre = 'Premium'),  'generar_reportes');
