-- Versión limpia para dbdiagram.io (sin PL/pgSQL ni DROP)

CREATE TABLE usuarios (
    usuario_id    SERIAL PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    email         VARCHAR(100) UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    rol           VARCHAR(20) NOT NULL,
    created_at    TIMESTAMP
);

CREATE TABLE planes (
    plan_id        SERIAL PRIMARY KEY,
    nombre         VARCHAR(20) UNIQUE NOT NULL,
    precio_mensual DECIMAL(10,2) NOT NULL
);

CREATE TABLE condominio (
    condominio_id SERIAL PRIMARY KEY,
    nombre        VARCHAR(100) NOT NULL,
    ubicacion     TEXT
);

CREATE TABLE suscripciones (
    suscripcion_id SERIAL PRIMARY KEY,
    condominio_id  INT REFERENCES condominio(condominio_id),
    plan_id        INT REFERENCES planes(plan_id),
    fecha_inicio   DATE,
    is_activo      BOOLEAN
);

CREATE TABLE plan_funcionalidades (
    plan_id       INT REFERENCES planes(plan_id),
    funcionalidad VARCHAR(50) NOT NULL,
    PRIMARY KEY (plan_id, funcionalidad)
);

CREATE TABLE camaras (
    camara_id        SERIAL PRIMARY KEY,
    condominio_id    INT REFERENCES condominio(condominio_id),
    nombre_ubicacion VARCHAR(100) NOT NULL,
    rtsp_url         TEXT NOT NULL,
    is_active        BOOLEAN
);

CREATE TABLE zonas_roi (
    roi_id               SERIAL PRIMARY KEY,
    camara_id            INT REFERENCES camaras(camara_id),
    poligono_coordenadas JSONB NOT NULL,
    tipo_zona            VARCHAR(50) NOT NULL
);

CREATE TABLE reglas_infraccion (
    regla_id     SERIAL PRIMARY KEY,
    nombre_regla VARCHAR(50) UNIQUE NOT NULL,
    descripcion  TEXT
);

CREATE TABLE eventos (
    evento_id             SERIAL PRIMARY KEY,
    camara_id             INT REFERENCES camaras(camara_id),
    regla_id              INT REFERENCES reglas_infraccion(regla_id),
    timestamp_deteccion   TIMESTAMP,
    confianza_ia          FLOAT NOT NULL,
    estado                VARCHAR(20),
    imagen_evidencia_path TEXT,
    resolucion            TEXT,
    atendido_por          INT REFERENCES usuarios(usuario_id),
    tiempo_respuesta      INTERVAL
);

CREATE TABLE logs_auditoria (
    log_id           SERIAL PRIMARY KEY,
    usuario_id       INT REFERENCES usuarios(usuario_id),
    accion           TEXT NOT NULL,
    tabla_afectada   VARCHAR(50),
    timestamp_accion TIMESTAMP
);

CREATE TABLE datasets (
    dataset_id     SERIAL PRIMARY KEY,
    nombre         VARCHAR(50) NOT NULL,
    version_modelo VARCHAR(20) NOT NULL
);

CREATE TABLE dataset_eventos (
    dataset_id        INT REFERENCES datasets(dataset_id),
    evento_id         INT REFERENCES eventos(evento_id),
    etiqueta_correcta VARCHAR(50),
    PRIMARY KEY (dataset_id, evento_id)
);

CREATE TABLE notificaciones (
    notificacion_id SERIAL PRIMARY KEY,
    evento_id       INT REFERENCES eventos(evento_id),
    usuario_id      INT NOT NULL REFERENCES usuarios(usuario_id),
    titulo          TEXT NOT NULL,
    cuerpo          TEXT,
    token_fcm       TEXT,
    estado          VARCHAR(20) DEFAULT 'enviada',
    created_at      TIMESTAMP
);
