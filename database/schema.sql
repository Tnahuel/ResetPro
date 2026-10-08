-- Esquema de referencia (PostgreSQL). La API crea estas tablas sola al arrancar
-- (backend/init_db.py), no hace falta ejecutarlo a mano.

CREATE TYPE rol_enum AS ENUM (usuario, profesor, admin);
CREATE TYPE estado_turno_enum AS ENUM (pendiente, confirmado, cancelado, completado);

CREATE TABLE credenciales (
    id               SERIAL PRIMARY KEY,
    email            VARCHAR(150) UNIQUE NOT NULL,
    contrasena_hash  VARCHAR(255) NOT NULL,
    rol              rol_enum NOT NULL,
    creado_en        TIMESTAMP DEFAULT NOW(),
    ultimo_acceso    TIMESTAMP
);

CREATE TABLE usuarios (
    id                     SERIAL PRIMARY KEY,
    credenciales_id        INTEGER UNIQUE NOT NULL REFERENCES credenciales(id) ON DELETE CASCADE,
    nombre                 VARCHAR(120) NOT NULL,
    edad                   INTEGER,
    altura                 FLOAT,
    peso                   FLOAT,
    imagen                 VARCHAR(255),
    grupo_muscular_actual  VARCHAR(60)
);

CREATE TABLE profesores (
    id                SERIAL PRIMARY KEY,
    credenciales_id   INTEGER UNIQUE NOT NULL REFERENCES credenciales(id) ON DELETE CASCADE,
    nombre            VARCHAR(120) NOT NULL,
    especialidad      VARCHAR(120),
    horarios          VARCHAR(255),
    horas_trabajadas  FLOAT DEFAULT 0
);

CREATE TABLE administradores (
    id               SERIAL PRIMARY KEY,
    credenciales_id  INTEGER UNIQUE NOT NULL REFERENCES credenciales(id) ON DELETE CASCADE,
    nombre           VARCHAR(120) NOT NULL,
    permisos         VARCHAR(120) DEFAULT total
);

CREATE TABLE dietas (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    archivo_pdf     VARCHAR(255),
    enlace_externo  VARCHAR(255),
    proteina        FLOAT DEFAULT 0,
    carbohidratos   FLOAT DEFAULT 0,
    grasas          FLOAT DEFAULT 0,
    micros          VARCHAR(255),
    tipo_dieta      VARCHAR(60),
    actualizado_en  TIMESTAMP DEFAULT NOW()
);

CREATE TABLE turnos (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    profesor_id     INTEGER NOT NULL REFERENCES profesores(id) ON DELETE CASCADE,
    fecha           DATE NOT NULL,
    rango_horario   VARCHAR(30) NOT NULL,
    estado          estado_turno_enum DEFAULT confirmado,
    grupo_muscular  VARCHAR(60),
    nota            INTEGER
);
CREATE INDEX ix_turnos_usuario ON turnos(usuario_id);
CREATE INDEX ix_turnos_profesor ON turnos(profesor_id);
CREATE INDEX ix_turnos_fecha ON turnos(fecha);

CREATE TABLE entrenamientos (
    id              SERIAL PRIMARY KEY,
    usuario_id      INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    profesor_id     INTEGER NOT NULL REFERENCES profesores(id) ON DELETE CASCADE,
    fecha           DATE NOT NULL,
    grupo_muscular  VARCHAR(60),
    notas           VARCHAR(255)
);

CREATE TABLE archivos (
    id          SERIAL PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    tipo        VARCHAR(20) NOT NULL,           -- rutina | dieta
    nombre      VARCHAR(255) NOT NULL,
    mime        VARCHAR(100) DEFAULT application/pdf,
    tamano      INTEGER DEFAULT 0,
    creado_en   TIMESTAMP DEFAULT NOW(),
    contenido   BYTEA NOT NULL
);
CREATE INDEX ix_archivos_usuario ON archivos(usuario_id);
