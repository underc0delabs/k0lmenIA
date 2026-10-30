-- Ejemplo de migración Flyway para probar el analizador.
ALTER TABLE pedidos ADD COLUMN estado VARCHAR(20) NOT NULL;
CREATE INDEX idx_pedidos_estado ON pedidos(estado);
