"""k0lmenaTMT: el gestor de pruebas de la suite k0lmena, por su server MCP con el token personal (kolm_pat_...).

Docs: el server MCP de k0lmenaTMT (POST {K0LMENA_TMT_URL}, por defecto http://localhost:4000/api/v1/mcp).

Por qué el script habla MCP y no el agente: con el token personal, k0lmenaTMT solo expone su server MCP (la API REST
pide el login de la interfaz). Si lo hiciera el agente, cada caso, cada resultado y cada evidencia (en base64) pasarían
por la conversación: cientos de llamadas y miles de tokens por corrida. El script hace las mismas llamadas sin modelo.

Cómo escribe k0lmenaTMT: cada herramienta de escritura (create_test_case, record_execution…) devuelve una PROPUESTA
(un change-set); el script la aplica con apply_change_set y toma el id que se creó. Todo queda registrado en
k0lmenaTMT y se puede deshacer desde ahí (undo_change_set).

Mapeo:
- carpeta    -> create_directory (anidadas, una por nivel). El MCP no lista carpetas: los ids se recuerdan en
                output/gestion/k0lmena-tmt.json para no duplicarlas.
- caso       -> create_test_case con pasos (acción, datos, resultado esperado), etiquetas (las del caso, la
                historia y "k0lmenIA"), tiempo estimado y prioridad (K0LMENA_TMT_PRIORIDADES). BDD: los pasos
                Given/When/Then como pasos del caso y automated=true.
- vínculo caso/ciclo-historia -> k0lmenaTMT no se conecta a Jira: la historia viaja como etiqueta del caso y en
                la descripción del ciclo.
- ciclo      -> create_test_cycle; agregar casos -> add_case_to_cycle (cada caso en el ciclo es un "cycle suite").
- resultado  -> record_execution (estado y conteo pass/fail/blocked, tiempo real) + attach_evidence (capturas,
                GIF, video y, como record_execution no tiene comentario, el detalle del resultado como
                resultado.txt). Hasta 10 archivos y 10 MB por archivo en cada llamada (límites de k0lmenaTMT).
- keys       -> "TC-<id>" (casos) y "CY-<id>" (ciclos), así se usan igual que las de Xray o Zephyr.
Ritmo: k0lmenaTMT acepta ASSISTANT_RATE_LIMIT pedidos por minuto por usuario (20 por defecto) y cada escritura son
dos (proponer y aplicar). K0LMENA_TMT_RPM ajusta el ritmo del script si en tu instancia es otro.
"""
import base64
import json
import os
import re
from pathlib import Path

from adaptadores.base import Adaptador, titulo_remoto, con_tiempo, tiempo_nativo
from comun import DIR_GESTION, ErrorGestion, Http, env

# estado normalizado -> (status del cycle suite, contador)
ESTADOS = {"aprobado": ("completed", "pass"), "fallido": ("failed", "fail"), "bloqueado": ("failed", "blocked"),
           "pendiente": ("pending", None), "en_ejecucion": ("running", None)}
MAX_ARCHIVOS = 10                   # MCP_MAX_ATTACHMENTS de k0lmenaTMT
MAX_ARCHIVO = 10 * 1024 * 1024      # MCP_MAX_EVIDENCE_BYTES
MAX_POR_LLAMADA = 9 * 1024 * 1024   # el cuerpo del pedido admite 15 MB y el base64 agranda un 33 %
MIME = {"png": "image/png", "gif": "image/gif", "jpg": "image/jpeg", "jpeg": "image/jpeg", "webm": "video/webm",
        "mp4": "video/mp4", "txt": "text/plain", "json": "application/json", "html": "text/html", "pdf": "application/pdf"}
_BDD = re.compile(r"^\s*(Given|When|Then|And|But|\*)\s+(.*)$")


class K0lmenaTMT(Adaptador):
    nombre = "k0lmena-tmt"
    limite_adjunto = MAX_ARCHIVO
    patron_key = r"^TC-\d+$"  # el tag de un escenario que ya trae la key de k0lmenaTMT (@TC-123)

    def __init__(self, proyecto, dry_run=False):
        super().__init__(proyecto, dry_run)
        if not str(proyecto).isdigit():
            raise ErrorGestion("Para k0lmenaTMT, GESTION_PROYECTO es el id numérico del proyecto (está en la URL del "
                               "proyecto en k0lmenaTMT, por ejemplo /projects/3).")
        self.project_id = int(proyecto)
        url = env("K0LMENA_TMT_URL", obligatoria=False, defecto="http://localhost:4000/api/v1/mcp")
        self.url = url
        token = "dry-run" if dry_run else env("K0LMENA_TMT_TOKEN")
        rpm = float(os.environ.get("K0LMENA_TMT_RPM", "20") or 20)
        self.http = Http(url, {"Authorization": f"Bearer {token}", "Accept": "application/json, text/event-stream"},
                         dry_run=dry_run, nombre="k0lmena-tmt", intervalo=60.0 / max(rpm, 1) + 0.1)
        self.prioridades = json.loads(os.environ.get("K0LMENA_TMT_PRIORIDADES", "{}") or "{}")
        self.estados = {**ESTADOS, **{k: tuple(v) for k, v in json.loads(os.environ.get("K0LMENA_TMT_ESTADOS", "{}") or "{}").items()}}
        self.historia = None  # la pone gestion.py (subir-casos --historia): va como etiqueta del caso
        self._memoria_ruta = DIR_GESTION / "k0lmena-tmt.json"
        self._memoria = self._leer_memoria()
        self._id = 0

    # --- MCP (sin el modelo en el medio) ----------------------------------------------
    def _llamar(self, herramienta, argumentos):
        self._id += 1
        cuerpo = {"jsonrpc": "2.0", "id": self._id, "method": "tools/call",
                  "params": {"name": herramienta, "arguments": argumentos}}
        r = self.http.post(self.url, json_body=cuerpo)
        if self.dry_run:
            return {"proposed": True, "changeSetId": self._id} if herramienta != "apply_change_set" else \
                {"status": "applied", "results": [{"targetId": 1000 + self._id}]}
        mensaje = _mensaje_jsonrpc(r)
        if "error" in mensaje:
            raise ErrorGestion(f"k0lmena-tmt: {herramienta}: {mensaje['error'].get('message', mensaje['error'])}")
        resultado = mensaje.get("result") or {}
        texto = "".join(c.get("text", "") for c in resultado.get("content") or [] if c.get("type") == "text")
        if resultado.get("isError"):
            raise ErrorGestion(f"k0lmena-tmt: {herramienta}: {texto[:600]}")
        try:
            return json.loads(texto) if texto else {}
        except ValueError:
            return {"texto": texto}

    def _escribir(self, herramienta, argumentos):
        """Propone y aplica (una escritura de k0lmenaTMT son dos pasos). Devuelve el id que se creó o modificó."""
        propuesta = self._llamar(herramienta, argumentos)
        if not propuesta.get("proposed") or not propuesta.get("changeSetId"):
            raise ErrorGestion(f"k0lmena-tmt: {herramienta} no devolvió una propuesta: {str(propuesta)[:400]}")
        aplicado = self._llamar("apply_change_set", {"id": propuesta["changeSetId"]})
        resultados = aplicado.get("results") or []
        fallas = [x for x in resultados if isinstance(x, dict) and (x.get("error") or x.get("status") == "failed")]
        if fallas or (aplicado.get("status") and aplicado["status"] not in ("applied", "done", "ok", "success")):
            raise ErrorGestion(f"k0lmena-tmt: no se pudo aplicar {herramienta}: {str(aplicado)[:500]}")
        ids = [x.get("targetId") for x in resultados if isinstance(x, dict) and x.get("targetId") is not None]
        return ids[0] if ids else None

    # --- memoria local (el MCP no lista carpetas ni los casos de un ciclo) --------------
    def _leer_memoria(self):
        try:
            datos = json.loads(self._memoria_ruta.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            datos = {}
        datos.setdefault("carpetas", {})
        datos.setdefault("suites", {})
        return datos

    def _guardar_memoria(self):
        if self.dry_run:
            return
        self._memoria_ruta.parent.mkdir(parents=True, exist_ok=True)
        self._memoria_ruta.write_text(json.dumps(self._memoria, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _id_de(key, prefijo):
        m = re.match(rf"^{prefijo}-(\d+)$", str(key or ""))
        if not m:
            raise ErrorGestion(f"'{key}' no es una key de k0lmenaTMT ({prefijo}-<id>).")
        return int(m.group(1))

    # --- repositorio ------------------------------------------------------------------
    def crear_carpeta(self, ruta):
        partes = [p for p in ruta.strip("/").split("/") if p]
        padre, camino = None, ""
        for parte in partes:
            camino += "/" + parte
            clave = f"{self.project_id}:{camino}"
            if clave not in self._memoria["carpetas"]:
                args = {"projectId": self.project_id, "name": parte}
                if padre:
                    args["parentDirectoryId"] = padre
                self._memoria["carpetas"][clave] = self._escribir("create_directory", args)
                self._guardar_memoria()
            padre = self._memoria["carpetas"][clave]
        return padre

    def crear_caso(self, caso, carpeta_id, carpeta_ruta):
        etiquetas = [e for e in caso.get("etiquetas", []) if e] + ([self.historia] if self.historia else []) + ["k0lmenIA"]
        args = {"projectId": self.project_id, "title": titulo_remoto(caso, 255),
                "description": con_tiempo(caso.get("descripcion", ""), caso), "precondition": caso.get("precondiciones", ""),
                "tags": list(dict.fromkeys(etiquetas))}
        if carpeta_id and not self.dry_run:
            args["directoryId"] = carpeta_id
        if caso.get("prioridad") in self.prioridades:
            args["priorityId"] = int(self.prioridades[caso["prioridad"]])
        if tiempo_nativo() and caso.get("estimacion"):
            args["estimatedDuration"] = max(1, round(caso["estimacion"]["segundos"] / 60))
        if caso["tipo"] == "cucumber":
            args["automated"] = True
            args["steps"] = [{"name": f"{m.group(1)} {m.group(2)}", "data": "", "expectedResult": ""}
                             for m in (_BDD.match(l) for l in caso.get("gherkin", "").splitlines()) if m]
            args["description"] = (args["description"] + "\n\n" + caso.get("gherkin", "")).strip()
        else:
            args["steps"] = [{"name": p["accion"], "data": p.get("datos", ""), "expectedResult": p.get("resultado", "")}
                             for p in caso.get("pasos", [])]
        nuevo = self._escribir("create_test_case", args)
        return {"key": f"TC-{nuevo}", "id": nuevo}

    def vincular_caso_historia(self, caso, historia):
        """k0lmenaTMT no se conecta a Jira: la historia ya viaja como etiqueta del caso (ver crear_caso)."""
        return None

    # --- ciclos -------------------------------------------------------------------------
    def crear_ciclo(self, nombre, descripcion="", carpeta_ruta=None):
        historia = f"Historia: {self.historia}" if self.historia else ""
        texto = "\n\n".join(x for x in (descripcion, historia, "Creado por k0lmenIA") if x)
        nuevo = self._escribir("create_test_cycle", {"projectId": self.project_id, "name": nombre[:255], "description": texto})
        return {"key": f"CY-{nuevo}", "id": nuevo}

    def vincular_ciclo_historia(self, ciclo, historia):
        return None  # va en la descripción del ciclo (crear_ciclo)

    def _suite(self, ciclo_id, caso_id, crear=True):
        clave = f"{ciclo_id}:{caso_id}"
        if clave not in self._memoria["suites"] and crear:
            self._memoria["suites"][clave] = self._escribir(
                "add_case_to_cycle", {"projectId": self.project_id, "testCycleId": ciclo_id, "testCaseId": caso_id})
            self._guardar_memoria()
        return self._memoria["suites"].get(clave)

    def agregar_casos_ciclo(self, ciclo, casos):
        ciclo_id = self._id_de(ciclo["key"], "CY")
        errores = []
        for caso in casos:
            try:
                self._suite(ciclo_id, self._id_de(caso["key"], "TC"))
            except ErrorGestion as e:
                errores.append(f'{caso["key"]}: {str(e)[:200]}')
        if errores:
            raise ErrorGestion("k0lmenaTMT no pudo agregar al ciclo: " + "; ".join(errores))

    # --- resultados ---------------------------------------------------------------------
    def registrar_resultado(self, ciclo, caso, estado, comentario, evidencias):
        ciclo_id, caso_id = self._id_de(ciclo["key"], "CY"), self._id_de(caso["key"], "TC")
        suite = self._suite(ciclo_id, caso_id)  # si el caso no estaba en el ciclo, se agrega (como en AIO)
        status, contador = self.estados[estado]
        args = {"projectId": self.project_id, "cycleSuiteId": suite, "status": status,
                "pass": 0, "fail": 0, "blocked": 0}
        if contador:
            args[contador] = 1
        duracion = re.search(r"\((\d+(?:\.\d+)?) ?s\)", comentario or "")
        if duracion:
            args["executionTimeMs"] = int(float(duracion.group(1)) * 1000)
        self._escribir("record_execution", args)
        # record_execution no tiene comentario: el detalle (escenario, error, falta información) va como archivo.
        archivos = [("resultado.txt", "text/plain", (comentario or "").encode("utf-8"))]
        no_subidas = []
        for archivo in evidencias:
            ruta = Path(archivo)
            if not ruta.exists():
                no_subidas.append((archivo, "no existe"))
                continue
            if ruta.stat().st_size > MAX_ARCHIVO:
                no_subidas.append((archivo, "supera 10 MB (subilo desde la interfaz de k0lmenaTMT)"))
                continue
            archivos.append((ruta.name, MIME.get(ruta.suffix.lstrip(".").lower(), "application/octet-stream"), ruta.read_bytes()))
        for tanda in _tandas(archivos):
            nombres = [n for n, _, _ in tanda]
            try:
                self._escribir("attach_evidence", {"projectId": self.project_id, "cycleSuiteId": suite, "files": [
                    {"fileName": n, "mimeType": m, "contentBase64": base64.b64encode(b).decode()} for n, m, b in tanda]})
            except ErrorGestion as e:
                no_subidas += [(n, str(e)[:200]) for n in nombres if n != "resultado.txt"]
        return no_subidas


def _tandas(archivos):
    """Agrupa los archivos en llamadas de hasta 10 archivos y ~9 MB (el pedido admite 15 MB con el base64)."""
    tanda, peso = [], 0
    for a in archivos:
        if tanda and (len(tanda) >= MAX_ARCHIVOS or peso + len(a[2]) > MAX_POR_LLAMADA):
            yield tanda
            tanda, peso = [], 0
        tanda.append(a)
        peso += len(a[2])
    if tanda:
        yield tanda


def _mensaje_jsonrpc(respuesta):
    """La respuesta del server MCP: JSON directo o un stream SSE (líneas "data: {...}")."""
    if isinstance(respuesta, dict) and ("result" in respuesta or "error" in respuesta):
        return respuesta
    texto = respuesta.get("texto", "") if isinstance(respuesta, dict) else str(respuesta)
    for linea in texto.splitlines():
        if linea.startswith("data:"):
            try:
                return json.loads(linea[5:].strip())
            except ValueError:
                continue
    raise ErrorGestion(f"k0lmena-tmt: respuesta inesperada del server MCP: {texto[:300]}")
