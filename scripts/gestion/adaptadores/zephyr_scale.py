"""Zephyr Scale (Zephyr para Jira Cloud): REST API v2.

Docs: https://support.smartbear.com/zephyr-scale-cloud/api-docs/  (OpenAPI oficial)
      https://support.smartbear.com/zephyr/docs/en/rest-api/api-access-tokens-management.html

Mapeo:
- carpeta  -> carpeta TEST_CASE (se busca nivel por nivel y se crea la que falta)
- caso     -> test case (pasos inline con testData y expectedResult; BDD: test script tipo "bdd")
- ciclo    -> test cycle (en la carpeta TEST_CYCLE de la misma ruta, si la hay)
- vínculo caso/ciclo-historia -> links/issues con el id numérico del issue (se resuelve con Jira REST)
- agregar al ciclo -> test execution "Not Executed" de cada caso (Zephyr no tiene otro modo de sumarlos)
- resultado -> test execution nueva con statusName, comment y executionTime + adjuntos (PUT .../attachments/<archivo>)
Rate limit: depende del plan; los 429 se reintentan con Retry-After (comun.Http).
"""
import base64
import json
import os
from pathlib import Path
from urllib.parse import quote

from adaptadores.base import Adaptador, titulo_remoto, con_tiempo, tiempo_nativo, intentar_con_tiempo
from comun import ErrorGestion, Http, env

# estado normalizado -> statusName por defecto de Zephyr (se puede pisar con ZEPHYR_ESTADOS)
ESTADOS = {"aprobado": "Pass", "fallido": "Fail", "bloqueado": "Blocked",
           "pendiente": "Not Executed", "en_ejecucion": "In Progress"}
# prioridad de k0lmenIA -> priorityName por defecto de Zephyr (High, Normal, Low); GESTION_PRIORIDADES la pisa
PRIORIDADES = {"Crítica": "High", "Alta": "High", "Media": "Normal", "Baja": "Low"}
MIME = {"png": "image/png", "gif": "image/gif", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "webm": "video/webm", "mp4": "video/mp4", "zip": "application/zip", "html": "text/html"}


class ZephyrScale(Adaptador):
    nombre = "zephyr-scale"
    limite_adjunto = 1024 * 1024 * 1024  # 1 GB por adjunto (API v2)

    def __init__(self, proyecto, dry_run=False):
        super().__init__(proyecto, dry_run)
        base = env("ZEPHYR_API_URL", obligatoria=False, defecto="https://api.zephyrscale.smartbear.com/v2")
        token = "dry-run" if dry_run else env("ZEPHYR_API_TOKEN")
        self.http = Http(base, {"Authorization": f"Bearer {token}"}, dry_run=dry_run, nombre="zephyr")
        self.estados = {**ESTADOS, **json.loads(os.environ.get("ZEPHYR_ESTADOS", "{}") or "{}")}
        self.prioridades = {**PRIORIDADES, **json.loads(os.environ.get("GESTION_PRIORIDADES", "{}") or "{}")}
        mb = float(os.environ.get("GESTION_LIMITE_ADJUNTO_MB", "0") or 0)
        if mb:
            self.limite_adjunto = int(mb * 1024 * 1024)
        self._jira = None
        self._ids = {}
        self._carpetas = {}

    # --- utilidades -------------------------------------------------------------------
    @property
    def jira(self):
        """Jira Cloud REST (email + API token): solo para pasar de key a id numérico en los vínculos."""
        if self._jira is None and self.dry_run:
            self._jira = Http("https://jira.dry-run", dry_run=True, nombre="jira")
        if self._jira is None:
            token = base64.b64encode(f'{env("JIRA_EMAIL")}:{env("JIRA_API_TOKEN")}'.encode()).decode()
            self._jira = Http(env("JIRA_BASE_URL"), {"Authorization": f"Basic {token}"},
                              dry_run=self.dry_run, nombre="jira")
        return self._jira

    def issue_id(self, key):
        """Zephyr vincula por id numérico del issue de Jira; lo resolvemos desde la key."""
        if self.dry_run:
            return 0
        if key not in self._ids:
            r = self.jira.get(f"/rest/api/3/issue/{key}", params={"fields": "id"})
            self._ids[key] = int(r["id"])
        return self._ids[key]

    def _carpetas_de(self, tipo):
        """Todas las carpetas del proyecto de ese tipo (TEST_CASE o TEST_CYCLE), paginando."""
        if tipo not in self._carpetas:
            todas, inicio = [], 0
            while not self.dry_run:
                r = self.http.get("/folders", params={"projectKey": self.proyecto, "folderType": tipo,
                                                      "maxResults": 1000, "startAt": inicio})
                valores = r.get("values") or []
                todas += valores
                if r.get("isLast", True) or not valores:
                    break
                inicio += len(valores)
            self._carpetas[tipo] = todas
        return self._carpetas[tipo]

    def _carpeta(self, tipo, ruta):
        """Busca la ruta nivel por nivel y crea lo que falta (idempotente). Devuelve el id de la última."""
        padre = None
        for nombre in [p for p in ruta.strip("/").split("/") if p]:
            existente = next((c for c in self._carpetas_de(tipo)
                              if c.get("name") == nombre and c.get("parentId") == padre), None)
            if existente:
                padre = existente["id"]
                continue
            cuerpo = {"name": nombre[:255], "projectKey": self.proyecto, "folderType": tipo}
            if padre is not None:
                cuerpo["parentId"] = padre
            nueva = self.http.post("/folders", json_body=cuerpo)
            self._carpetas_de(tipo).append({"id": nueva.get("id"), "name": nombre, "parentId": padre})
            padre = nueva.get("id")
        return padre

    # --- repositorio ------------------------------------------------------------------
    def crear_carpeta(self, ruta):
        return self._carpeta("TEST_CASE", ruta)

    def crear_caso(self, caso, carpeta_id, carpeta_ruta):
        cuerpo = {
            "projectKey": self.proyecto,
            "name": titulo_remoto(caso, 255),
            "objective": con_tiempo(caso.get("descripcion", ""), caso),
            "precondition": caso.get("precondiciones", ""),
            "labels": [e.replace(" ", "_") for e in caso.get("etiquetas", [])] + ["k0lmenIA"],
        }
        if carpeta_id and not self.dry_run:
            cuerpo["folderId"] = carpeta_id
        prioridad = self.prioridades.get(caso.get("prioridad"))
        if prioridad and os.environ.get("GESTION_ENVIAR_PRIORIDAD", "1") != "0":
            cuerpo["priorityName"] = prioridad
        con = cuerpo
        if tiempo_nativo() and caso.get("estimacion"):
            con = {**cuerpo, "estimatedTime": int(caso["estimacion"]["segundos"] * 1000)}  # en milisegundos
        r = intentar_con_tiempo(lambda c: self.http.post("/testcases", json_body=c), con, cuerpo)
        key = r.get("key")
        if caso["tipo"] == "cucumber":
            self.http.post(f"/testcases/{key}/testscript", json_body={"type": "bdd", "text": caso["gherkin"]})
        elif caso.get("pasos"):
            self.http.post(f"/testcases/{key}/teststeps", json_body={"mode": "OVERWRITE", "items": [
                {"inline": {"description": p["accion"], "testData": p["datos"], "expectedResult": p["resultado"]}}
                for p in caso["pasos"]]})
        return {"key": key, "id": r.get("id")}

    def vincular_caso_historia(self, caso, historia):
        self.http.post(f'/testcases/{caso["key"]}/links/issues', json_body={"issueId": self.issue_id(historia)})

    # --- ciclos -------------------------------------------------------------------------
    def crear_ciclo(self, nombre, descripcion="", carpeta_ruta=None):
        cuerpo = {"projectKey": self.proyecto, "name": nombre[:255], "description": descripcion}
        if carpeta_ruta:
            carpeta = self._carpeta("TEST_CYCLE", carpeta_ruta)
            if carpeta and not self.dry_run:
                cuerpo["folderId"] = carpeta
        r = self.http.post("/testcycles", json_body=cuerpo)
        return {"key": r.get("key"), "id": r.get("id")}

    def vincular_ciclo_historia(self, ciclo, historia):
        self.http.post(f'/testcycles/{ciclo["key"]}/links/issues', json_body={"issueId": self.issue_id(historia)})

    def agregar_casos_ciclo(self, ciclo, casos):
        """Zephyr no tiene 'agregar caso al ciclo': un caso está en el ciclo cuando tiene una ejecución ahí."""
        errores = []
        for caso in casos:
            try:
                self.http.post("/testexecutions", json_body={
                    "projectKey": self.proyecto, "testCaseKey": caso["key"], "testCycleKey": ciclo["key"],
                    "statusName": self.estados["pendiente"]})
            except ErrorGestion as e:
                errores.append(f'{caso["key"]}: {str(e)[:200]}')
        if errores:
            raise ErrorGestion("Zephyr no pudo agregar al ciclo: " + "; ".join(errores))

    # --- resultados ---------------------------------------------------------------------
    def registrar_resultado(self, ciclo, caso, estado, comentario, evidencias):
        r = self.http.post("/testexecutions", json_body={
            "projectKey": self.proyecto, "testCaseKey": caso["key"], "testCycleKey": ciclo["key"],
            "statusName": self.estados[estado], "comment": comentario.replace("\n", "<br>"), "automated": True})
        ejecucion = r.get("id")
        no_subidas = []
        for archivo in evidencias:
            ruta = Path(archivo)
            if ruta.stat().st_size > self.limite_adjunto:
                no_subidas.append((archivo, f"supera {self.limite_adjunto // (1024 * 1024)} MB"))
                continue
            mime = MIME.get(ruta.suffix.lstrip(".").lower(), "application/octet-stream")
            try:
                self.http.put(f"/testexecutions/{ejecucion}/attachments/{quote(ruta.name)}",
                              data=ruta.read_bytes(), headers={"Content-Type": mime})
            except ErrorGestion as e:
                no_subidas.append((archivo, str(e)[:200]))
        return no_subidas
