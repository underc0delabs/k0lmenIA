"""Xray Server / Data Center: REST de Xray (/rest/raven/1.0) + REST de Jira (/rest/api/2).

Docs: https://docs.getxray.app/display/XRAY/REST+API

Mapeo:
- carpeta  -> carpeta del Test Repository (se crea nivel por nivel; raíz = -1)
- caso     -> issue "Test" (Manual: pasos con la API de steps; Cucumber: campos Cucumber Test Type
              y Cucumber Scenario). Los ids de los custom fields se descubren en tiempo de ejecución.
- ciclo    -> issue "Test Execution"
- vínculo caso-historia  -> issue link de Jira tipo "Tests" (el que tiene outward = "tests")
- vínculo ciclo-historia -> issue link "Relates"
"""
import base64
import json
import os
import re
from pathlib import Path

from adaptadores.base import Adaptador, titulo_remoto
from comun import ErrorGestion, Http, env

ESTADOS = {"aprobado": "PASS", "fallido": "FAIL", "pendiente": "TODO",
           "en_ejecucion": "EXECUTING", "bloqueado": "ABORTED"}
PRIORIDADES = {"Crítica": "Highest", "Alta": "High", "Media": "Medium", "Baja": "Low"}


class XrayDC(Adaptador):
    nombre = "xray-dc"

    def __init__(self, proyecto, dry_run=False):
        super().__init__(proyecto, dry_run)
        headers = {"Accept": "application/json"}
        if dry_run:
            headers["Authorization"] = "Bearer dry-run"
        elif os.environ.get("XRAY_DC_TOKEN", "").strip():
            headers["Authorization"] = f'Bearer {env("XRAY_DC_TOKEN")}'
        else:
            cred = base64.b64encode(f'{env("XRAY_DC_USER")}:{env("XRAY_DC_PASSWORD")}'.encode()).decode()
            headers["Authorization"] = f"Basic {cred}"
        self.http = Http(env("XRAY_DC_URL") if not dry_run else "https://jira.dry-run",
                         headers, dry_run=dry_run, nombre="xray-dc")
        self.estados = {**ESTADOS, **json.loads(os.environ.get("XRAY_ESTADOS", "{}") or "{}")}
        self.prioridades = {**PRIORIDADES, **json.loads(os.environ.get("GESTION_PRIORIDADES", "{}") or "{}")}
        mb = float(os.environ.get("GESTION_LIMITE_ADJUNTO_MB", "10") or 10)  # default de Jira: 10 MB
        self.limite_adjunto = int(mb * 1024 * 1024)
        self._campos = None
        self._link_caso = None

    # --- utilidades ---------------------------------------------------------------------
    def campo(self, nombre):
        """Id del custom field de Xray por nombre (varía en cada instancia)."""
        if self._campos is None:
            self._campos = {} if self.dry_run else {f["name"]: f["id"] for f in self.http.get("/rest/api/2/field")}
        if self.dry_run:
            return f"customfield({nombre})"
        if nombre not in self._campos:
            raise ErrorGestion(f"Jira no tiene el campo '{nombre}'. ¿Xray está instalado en esta instancia?")
        return self._campos[nombre]

    def _tipo_link_caso(self):
        if self._link_caso is None:
            self._link_caso = os.environ.get("XRAY_LINK_CASO", "").strip()
            if not self._link_caso:
                self._link_caso = "Tests"
                if not self.dry_run:
                    tipos = self.http.get("/rest/api/2/issueLinkType").get("issueLinkTypes", [])
                    self._link_caso = next((t["name"] for t in tipos if t.get("outward", "").lower() == "tests"), "Tests")
        return self._link_caso

    def _link(self, tipo, origen_key, destino_key):
        inward, outward = origen_key, destino_key
        if os.environ.get("XRAY_LINK_INVERTIR", "").strip() in ("1", "true", "on"):
            inward, outward = outward, inward
        self.http.post("/rest/api/2/issueLink", json_body={
            "type": {"name": tipo}, "inwardIssue": {"key": inward}, "outwardIssue": {"key": outward}})

    def _crear_issue(self, fields):
        r = self.http.post("/rest/api/2/issue", json_body={"fields": {"project": {"key": self.proyecto}, **fields}})
        return {"key": r.get("key"), "id": r.get("id")}

    # --- repositorio --------------------------------------------------------------------
    def crear_carpeta(self, ruta):
        base = f"/rest/raven/1.0/api/testrepository/{self.proyecto}/folders"
        arbol = [] if self.dry_run else self.http.get(base).get("folders", [])
        padre_id, hijos = -1, arbol
        for parte in [p for p in ruta.strip("/").split("/") if p]:
            existente = next((f for f in hijos if f.get("name") == parte), None)
            if existente:
                padre_id, hijos = existente["id"], existente.get("folders") or []
            else:
                r = self.http.post(f"{base}/{padre_id}", json_body={"name": parte})
                padre_id, hijos = r.get("id"), []
        return padre_id

    def crear_caso(self, caso, carpeta_id, carpeta_ruta):
        descripcion = caso.get("descripcion", "")
        if caso.get("precondiciones"):
            descripcion += f"\n\nPrecondiciones: {caso['precondiciones']}"
        fields = {
            "issuetype": {"name": "Test"},
            "summary": titulo_remoto(caso, 250),
            "description": descripcion.strip() or caso["titulo"],
            "labels": [e.replace(" ", "_") for e in caso.get("etiquetas", [])] + ["k0lmenIA"],
        }
        prioridad = self.prioridades.get(caso.get("prioridad"))
        if prioridad and os.environ.get("GESTION_ENVIAR_PRIORIDAD", "1") != "0":
            fields["priority"] = {"name": prioridad}
        if caso["tipo"] == "cucumber":
            # El campo Cucumber Scenario lleva solo los pasos (sin la línea "Scenario:"); el Background va a la descripción.
            lineas = caso["gherkin"].splitlines()
            esquema = any(re.match(r"^\s*Scenario (Outline|Template):", l) for l in lineas)
            inicio = next((i for i, l in enumerate(lineas) if re.match(r"^\s*(Scenario|Example)", l)), -1)
            fondo = "\n".join(l.strip() for l in lineas[:inicio] if l.strip()) if inicio > 0 else ""
            if fondo:
                fields["description"] += f"\n\n{fondo}"
            fields[self.campo("Test Type")] = {"value": "Cucumber"}
            fields[self.campo("Cucumber Test Type")] = {"value": "Scenario Outline" if esquema else "Scenario"}
            fields[self.campo("Cucumber Scenario")] = "\n".join(l.strip() for l in lineas[inicio + 1:] if l.strip())
            creado = self._crear_issue(fields)
        else:
            fields[self.campo("Test Type")] = {"value": "Manual"}
            creado = self._crear_issue(fields)
            for p in caso["pasos"]:
                self.http.put(f'/rest/raven/1.0/api/test/{creado["key"]}/step',
                              json_body={"step": p["accion"], "data": p["datos"], "result": p["resultado"]})
        if carpeta_id not in (None, -1):
            errores = self.http.put(f"/rest/raven/1.0/api/testrepository/{self.proyecto}/folders/{carpeta_id}/tests",
                                    json_body={"add": [creado["key"]]})
            if isinstance(errores, list) and errores:
                raise ErrorGestion(f"Xray no movió {creado['key']} a la carpeta: {errores}")
        return creado

    def vincular_caso_historia(self, caso, historia):
        self._link(self._tipo_link_caso(), caso["key"], historia)

    # --- ciclos -------------------------------------------------------------------------
    def crear_ciclo(self, nombre, descripcion="", carpeta_ruta=None):
        fields = {"issuetype": {"name": "Test Execution"}, "summary": nombre[:250], "labels": ["k0lmenIA"]}
        if descripcion:
            fields["description"] = descripcion
        return self._crear_issue(fields)

    def vincular_ciclo_historia(self, ciclo, historia):
        self._link(os.environ.get("XRAY_LINK_CICLO", "Relates"), ciclo["key"], historia)

    def agregar_casos_ciclo(self, ciclo, casos):
        self.http.post(f'/rest/raven/1.0/api/testexec/{ciclo["key"]}/test',
                       json_body={"add": [c["key"] for c in casos]})

    # --- resultados ---------------------------------------------------------------------
    def _run_id(self, ciclo, caso):
        params = {"testExecIssueKey": ciclo["key"], "testIssueKey": caso["key"]}
        try:
            return self.http.get("/rest/raven/1.0/api/testrun", params=params)["id"]
        except (ErrorGestion, KeyError):
            self.agregar_casos_ciclo(ciclo, [caso])  # el caso no estaba en la ejecución
            return self.http.get("/rest/raven/1.0/api/testrun", params=params)["id"]

    def registrar_resultado(self, ciclo, caso, estado, comentario, evidencias):
        run_id = self._run_id(ciclo, caso)
        self.http.put(f"/rest/raven/1.0/api/testrun/{run_id}",
                      json_body={"status": self.estados[estado], "comment": comentario})
        no_subidas = []
        for archivo in evidencias:
            ruta = Path(archivo)
            if ruta.stat().st_size * 4 / 3 > self.limite_adjunto:  # base64 agrega ~33%
                no_subidas.append((archivo, f"supera el límite de adjuntos ({self.limite_adjunto // 1048576} MB)"))
                continue
            mime = {"png": "image/png", "gif": "image/gif", "webm": "video/webm", "mp4": "video/mp4"}.get(
                ruta.suffix.lstrip(".").lower(), "application/octet-stream")
            datos = "<base64>" if self.dry_run else base64.b64encode(ruta.read_bytes()).decode()
            try:
                self.http.post(f"/rest/raven/1.0/api/testrun/{run_id}/attachment",
                               json_body={"data": datos, "filename": ruta.name, "contentType": mime})
            except ErrorGestion as e:
                no_subidas.append((archivo, str(e)[:200]))
        return no_subidas
