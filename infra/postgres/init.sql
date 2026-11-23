-- Inicialización de Postgres para el entorno local.
-- La base principal (POSTGRES_DB) la crea la imagen; aquí sólo extensiones y la base de Evolution API.
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_trgm;  -- búsqueda difusa de contactos

CREATE DATABASE evolution;
