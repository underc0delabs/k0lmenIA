# Scalar

Herramienta del agente `probador-scalar` (skill `pruebas-scalar`) para trabajar con [Scalar](https://scalar.com): el **Registry** de documentos OpenAPI, la **CLI** oficial (`@scalar/cli`) y los **tests** del cliente de Scalar (scripts `pm` en `x-post-response`). El **MCP** de Scalar se conecta aparte: `npm run conector -- activar scalar` (ver `CONECTORES.md`).

```bash
npm run scalar -- descargar --namespace mi-equipo --slug pagos            # → input/api/scalar/pagos.json
npm run scalar -- listar --namespace mi-equipo
npm run scalar -- coleccion --openapi input/api/scalar/pagos.json --casos output/scalar/pagos/casos.json
npm run scalar -- enriquecer --openapi input/api/scalar/pagos.json --casos output/scalar/pagos/casos.json
npm run scalar -- validar output/scalar/pagos/pagos.k0lmenia.json
npm run scalar -- publicar output/scalar/pagos/pagos.k0lmenia.json --namespace mi-equipo --slug pagos --version 1.4.0-qa --confirmar
```

- **`coleccion`** arma una colección de Postman v2.1 con un request por caso y sus `pm.test` (status, cuerpo esperado, campos, headers, tiempo y el schema de la respuesta documentada). Corre con `python scripts/correr_newman.py` y se importa en el cliente de Scalar.
- **`enriquecer`** deja una copia del OpenAPI con un ejemplo por caso y los tests en `x-post-response` de cada operación (entre marcas `k0lmenIA:inicio/fin`, sin pisar scripts escritos a mano).
- **`publicar`** tiene efecto: sin `--confirmar` no hace nada; publica privada por defecto (`--publica` para lo contrario) y no pisa una versión salvo `--forzar`.

Variables del `.env`: `SCALAR_API_KEY` (token personal: APIs privadas del Registry y la CLI; se pasa por variable de entorno, nunca en la línea de comandos), `SCALAR_NAMESPACE` (namespace por defecto) y, para el conector, `SCALAR_MCP_URL`. La CLI se usa con `npx`, así que hace falta Node.js 20+.
