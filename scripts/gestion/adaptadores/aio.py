"""AIO Tests (Jira Cloud): API REST pública v1.

Docs: https://tcms.aiojiraapps.com/aio-tcms/aiotcms-static/api-docs/  (OpenAPI oficial)
      https://aiosupport.atlassian.net/wiki/spaces/AioTests

Mapeo:
- carpeta  -> carpeta de casos (PUT .../testcase/folder/hierarchy, idempotente)
- caso     -> caso AIO (Classic con pasos o BDD con pasos Given/When/Then), estado "Published"
              (AIO solo deja agregar a un ciclo casos publicados)
- ciclo    -> test cycle (vínculo a la historia en jiraTaskIDs)
- vínculo caso-historia -> jiraRequirementIDs del caso
- resultado -> test run del caso en el ciclo + adjuntos al run
Rate limit: 60 requests por minuto -> 1 request por segundo.
"""
import json
import os
import re
from pathlib import Path

from adaptadores.base import Adaptador, titulo_remoto
from comun import ErrorGestion, Http, env

ESTADOS = {"aprobado": "Passed", "fallido": "Failed", "bloqueado": "Blocked",
           "pendiente": "Not Run", "en_ejecucion": "In Progress"}
PRIORIDADES = {"Crítica": ["critical", "highest", "blocker"], "Alta": ["high"],
               "Media": ["medium", "normal"], "Baja": ["low", "lowest"]}
BDD = {"given": "BDD_GIVEN", "when": "BDD_WHEN", "then": "BDD_THEN", "and": "BDD_AND",
       "but": "BDD_BUT", "*": "BDD_STAR"}


class AIO(Adaptador):
    nombre = "aio"
    limite_adjunto = 100 * 1024 * 1024  # 100 MB (KB de AIO, subida de evidencias)

    def __init__(self, proyecto, dry_run=False):
        super().__init__(proyecto, dry_run)
        base = env("AIO_API_URL", obligatoria=False, defecto="https://tcms.aiojiraapps.com/aio-tcms/api/v1")
        token = "dry-run" if dry_run else env("AIO_API_TOKEN")
        self.http = Http(base, {"Authorization": f"AioAuth {token}"}, dry_run=dry_run,
                         nombre="aio", intervalo=1.0)
        self.p = f"/project/{proyecto}"
        self.estados = {**ESTADOS, **json.loads(os.environ.get("AIO_ESTADOS", "{}") or "{}")}
        self._config = {}

    # --- catálogos de la instancia (ids) --------------------------------------------
    def _catalogo(self, ruta):
        if ruta not in self._config:
            self._config[ruta] = [] if self.dry_run else (self.http.get(f"{self.p}/config/{ruta}") or [])
        return self._config[ruta]

    def _id_por_nombre(self, ruta, nombres):
        for item in self._catalogo(ruta):
            if str(item.get("name", "")).strip().lower() in nombres:
                return item["ID"]
        return None

    def _tags(self, nombres):
        if not nombres or self.dry_run:
            return []
        existentes = {t["name"].lower(): t["ID"] for t in (self.http.get(f"{self.p}/tag") or [])}
        nuevos = [{"name": n} for n in nombres if n.lower() not in existentes]
        if nuevos:
            for t in self.http.post(f"{self.p}/tag", json_body=nuevos) or []:
                existentes[t["name"].lower()] = t["ID"]
        return [{"tag": {"ID": existentes[n.lower()]}} for n in nombres if n.lower() in existentes]

    @staticmethod
    def _pasos_bdd(gherkin):
        """Gherkin del escenario -> pasos BDD de AIO. Tablas y docstrings se pegan al paso anterior;
        Background y Examples van a la descripción."""
        pasos, extra, seccion = [], [], None
        for linea in gherkin.splitlines():
            l = linea.strip()
            if not l:
                continue
            if re.match(r"^(Background|Examples|Scenarios):", l):
                seccion = l.split(":")[0]
                extra.append(l)
                continue
            if re.match(r"^(Scenario|Scenario Outline|Scenario Template|Example):", l):
                seccion = None
                continue
            palabra = l.split(" ", 1)[0].lower()
            if seccion is None and palabra in BDD:
                pasos.append({"stepType": BDD[palabra], "gherkinKeyword": l.split(" ", 1)[0],
                              "bddStep": l.split(" ", 1)[1] if " " in l else ""})
            elif seccion is None and pasos:
                pasos[-1]["bddStep"] += "\n" + l
            else:
                extra.append(l)
        return pasos, "\n".join(extra)

    # --- repositorio ------------------------------------------------------------------
    def crear_carpeta(self, ruta):
        partes = [p for p in ruta.strip("/").split("/") if p]
        r = self.http.put(f"{self.p}/testcase/folder/hierarchy",
                          json_body={"baseFolderId": None, "folderHierarchy": partes})
        return r.get("ID")

    def crear_caso(self, caso, carpeta_id, carpeta_ruta):
        estado_caso = os.environ.get("AIO_ESTADO_CASO", "Published").strip().lower()
        cuerpo = {
            "title": titulo_remoto(caso, 255),
            "description": caso.get("descripcion", ""),
            "precondition": caso.get("precondiciones", ""),
            "folder": {"ID": carpeta_id},
            "tags": self._tags(caso.get("etiquetas", []) + ["k0lmenIA"]),
        }
        status_id = self._id_por_nombre("testcase/status", {estado_caso})
        if status_id:
            cuerpo["status"] = {"ID": status_id}
        elif not self.dry_run:
            raise ErrorGestion(f"AIO no tiene el estado de caso '{estado_caso}' (AIO_ESTADO_CASO). "
                               "Solo los casos publicados se pueden agregar a un ciclo.")
        prioridad_id = self._id_por_nombre("testcase/priority", set(PRIORIDADES.get(caso.get("prioridad"), [])))
        if prioridad_id:
            cuerpo["priority"] = {"ID": prioridad_id}
        if caso["tipo"] == "cucumber":
            pasos, extra = self._pasos_bdd(caso["gherkin"])
            script_id = self._id_por_nombre("testcase/scripttype", {"bdd"})
            if script_id:
                cuerpo["scriptType"] = {"ID": script_id}
            cuerpo["steps"] = pasos
            if extra:
                cuerpo["description"] = (cuerpo["description"] + "\n\n" + extra).strip()
        else:
            script_id = self._id_por_nombre("testcase/scripttype", {"classic"})
            if script_id:
                cuerpo["scriptType"] = {"ID": script_id}
            cuerpo["steps"] = [{"stepType": "TEXT", "step": p["accion"], "data": p["datos"],
                                "expectedResult": p["resultado"]} for p in caso["pasos"]]
        r = self.http.post(f"{self.p}/testcase", json_body=cuerpo)
        return {"key": r.get("key"), "id": r.get("ID")}

    def vincular_caso_historia(self, caso, historia):
        """AIO no tiene un endpoint de vínculo: se lee el caso, se suma la historia a
        jiraRequirementIDs y se vuelve a guardar el caso completo."""
        ruta = f'{self.p}/testcase/{caso["key"]}/detail'
        detalle = self.http.get(ruta)
        if self.dry_run:
            detalle = {}
        actuales = [str(x) for x in detalle.get("jiraRequirementIDs") or []]
        if historia not in actuales:
            detalle["jiraRequirementIDs"] = actuales + [historia]
            self.http.put(ruta, json_body=detalle)

    # --- ciclos -------------------------------------------------------------------------
    def crear_ciclo(self, nombre, descripcion="", carpeta_ruta=None):
        cuerpo = {"title": nombre[:255], "objective": descripcion}
        if carpeta_ruta:
            partes = [p for p in carpeta_ruta.strip("/").split("/") if p]
            carpeta = self.http.put(f"{self.p}/testcycle/folder/hierarchy",
                                    json_body={"baseFolderId": None, "folderHierarchy": partes})
            if carpeta.get("ID") and not self.dry_run:
                cuerpo["folder"] = {"ID": carpeta["ID"]}
        r = self.http.post(f"{self.p}/testcycle/detail", json_body=cuerpo)
        return {"key": r.get("key"), "id": r.get("ID")}

    def vincular_ciclo_historia(self, ciclo, historia):
        ruta = f'{self.p}/testcycle/{ciclo["key"]}/detail'
        detalle = {} if self.dry_run else self.http.get(ruta)
        actuales = [str(x) for x in detalle.get("jiraTaskIDs") or []]
        if historia not in actuales:
            detalle["jiraTaskIDs"] = actuales + [historia]
            self.http.put(ruta, json_body=detalle)

    def agregar_casos_ciclo(self, ciclo, casos):
        keys = [c["key"] for c in casos]
        errores = {}
        for i in range(0, len(keys), 100):
            r = self.http.post(f'{self.p}/testcycle/{ciclo["key"]}/bulk/testrun/update',
                               params={"addCaseToCycle": "true"},
                               json_body={"testRuns": [{"testCaseKey": k} for k in keys[i:i + 100]]})
            errores.update(r.get("errors") or {})
        if errores:
            raise ErrorGestion("AIO no pudo agregar al ciclo: " +
                               "; ".join(f"{k}: {v.get('message', v)}" for k, v in errores.items()))

    # --- resultados ---------------------------------------------------------------------
    def registrar_resultado(self, ciclo, caso, estado, comentario, evidencias):
        r = self.http.post(f'{self.p}/testcycle/{ciclo["key"]}/testcase/{caso["key"]}/testrun',
                           params={"createNewRun": "true", "addCaseToCycle": "true"},
                           json_body={"testRunStatus": self.estados[estado], "isAutomated": True,
                                      "comments": [comentario]})
        run_id = r.get("ID")
        no_subidas = []
        for archivo in evidencias:
            ruta = Path(archivo)
            if ruta.stat().st_size > self.limite_adjunto:
                no_subidas.append((archivo, "supera 100 MB"))
                continue
            mime = {"png": "image/png", "gif": "image/gif", "webm": "video/webm", "mp4": "video/mp4"}.get(
                ruta.suffix.lstrip(".").lower(), "application/octet-stream")
            try:
                with open(ruta, "rb") as f:
                    self.http.post(f'{self.p}/testcycle/{ciclo["key"]}/testrun/{run_id}/attachment',
                                   files={"file": (ruta.name, f, mime)})
            except ErrorGestion as e:
                no_subidas.append((archivo, str(e)[:200]))
        return no_subidas
