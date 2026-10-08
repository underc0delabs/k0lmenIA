"""QMetry Test Management for Jira Cloud (QTM4J): Open API (/rest/api/latest).

Docs: https://app.swaggerhub.com/apis-docs/qmetry-ada/qtm4j_cloud/restapi
      https://support.smartbear.com/qmetry-test-management-for-jira-cloud/docs/

Mapeo:
- carpeta  -> carpeta de test cases (se crea nivel por nivel)
- caso     -> test case (pasos manuales; BDD: se crea y luego se carga bddScenario en la versión)
- ciclo    -> test cycle
- vínculo caso/ciclo-historia -> requirements/link con JQL por key (no hace falta el id de Jira)
- resultado -> test case execution del ciclo (executionResultId + comment) y adjuntos vía URL firmada de S3
Rate limit: 10.000 llamadas por hora para toda la instancia.
"""
import json
import os
from pathlib import Path

from adaptadores.base import Adaptador, titulo_remoto
from comun import ErrorGestion, Http, env, necesitar

# estado normalizado -> defaultName de QTM4J (el "name" puede estar personalizado)
ESTADOS = {"aprobado": "Pass", "fallido": "Fail", "bloqueado": "Blocked",
           "pendiente": "Not Executed", "en_ejecucion": "WIP"}
PRIORIDADES = {"Crítica": ["blocker", "critical", "highest"], "Alta": ["high", "major"],
               "Media": ["medium", "normal"], "Baja": ["low", "minor", "lowest"]}


class QTM4J(Adaptador):
    nombre = "qtm4j"

    def __init__(self, proyecto, dry_run=False):
        super().__init__(proyecto, dry_run)
        base = env("QTM4J_BASE_URL", obligatoria=False, defecto="https://qtmcloud.qmetry.com")
        clave = "dry-run" if dry_run else env("QTM4J_API_KEY")
        self.http = Http(f"{base.rstrip('/')}/rest/api/latest",
                         {"apiKey": clave, "Content-Type": "application/json"}, dry_run=dry_run, nombre="qtm4j")
        self.estados = {**ESTADOS, **json.loads(os.environ.get("QTM4J_ESTADOS", "{}") or "{}")}
        self._project_id = None
        self._cache = {}

    # --- utilidades -------------------------------------------------------------------
    @property
    def project_id(self):
        if self._project_id is None:
            if self.dry_run:
                self._project_id = 0
            else:
                r = self.http.post("/projects", params={"maxResults": 100},
                                   json_body={"search": self.proyecto, "qmetryEnabled": True})
                for p in r.get("data", []):
                    if p.get("key") == self.proyecto:
                        self._project_id = p["id"]
                if self._project_id is None:
                    raise ErrorGestion(f"QTM4J no encuentra el proyecto {self.proyecto} (¿QMetry está habilitado?).")
        return self._project_id

    def _lista(self, ruta):
        if ruta not in self._cache:
            r = [] if self.dry_run else self.http.get(f"/projects/{self.project_id}/{ruta}")
            self._cache[ruta] = r.get("data", r) if isinstance(r, dict) else r
        return self._cache[ruta]

    def _id_por_nombre(self, ruta, nombres, campo="name"):
        for item in self._lista(ruta) or []:
            if str(item.get(campo, "")).strip().lower() in nombres:
                return item["id"]
        return None

    def _labels(self, nombres):
        ids = []
        for n in nombres:
            i = self._id_por_nombre("labels", {n.lower()})
            if i is None and not self.dry_run:
                i = self.http.post(f"/projects/{self.project_id}/labels", json_body={"name": n}).get("id")
                self._cache.pop("labels", None)
            if i is not None:
                ids.append(i)
        return ids

    def _caso(self, caso):
        """key -> {id, versionNo} (las operaciones usan el id interno y la versión)."""
        if caso.get("id") and caso.get("versionNo"):
            return caso
        if self.dry_run:
            return {**caso, "id": f'id({caso["key"]})', "versionNo": 1}
        r = self.http.post("/testcases/search", params={"maxResults": 1},
                           json_body={"filter": {"projectId": self.project_id, "key": caso["key"]}})
        datos = (r.get("data") or [])
        if not datos:
            raise ErrorGestion(f"QTM4J no encuentra el caso {caso['key']}.")
        d = datos[0]
        return {**caso, "id": d["id"], "versionNo": (d.get("version") or {}).get("versionNo", 1)}

    def _ciclo_id(self, ciclo):
        if ciclo.get("id"):
            return ciclo["id"]
        if self.dry_run:
            return f'id({ciclo["key"]})'
        r = self.http.post("/testcycles/search", params={"maxResults": 1},
                           json_body={"filter": {"projectId": self.project_id, "key": ciclo["key"]}})
        datos = r.get("data") or []
        if not datos:
            raise ErrorGestion(f"QTM4J no encuentra el ciclo {ciclo['key']}.")
        return datos[0]["id"]

    def _carpeta(self, tipo, ruta):
        """Crea la ruta de carpetas nivel por nivel (tipo: testcase-folders | testcycle-folders)."""
        arbol = [] if self.dry_run else self.http.get(f"/projects/{self.project_id}/{tipo}").get("data", [])
        padre_id, hijos = -1, arbol
        for parte in [p for p in ruta.strip("/").split("/") if p]:
            existente = next((f for f in hijos if f.get("name") == parte), None)
            if existente:
                padre_id, hijos = existente["id"], existente.get("children") or []
            else:
                r = self.http.post(f"/projects/{self.project_id}/{tipo}",
                                   json_body={"folderName": parte, "parentId": padre_id})
                padre_id, hijos = r.get("id"), []
        return padre_id

    # --- repositorio --------------------------------------------------------------------
    def crear_carpeta(self, ruta):
        return self._carpeta("testcase-folders", ruta)

    def crear_caso(self, caso, carpeta_id, carpeta_ruta):
        cuerpo = {
            "projectId": self.project_id,
            "summary": titulo_remoto(caso, 255),
            "description": caso.get("descripcion", ""),
            "precondition": caso.get("precondiciones", ""),
            "folderId": carpeta_id,
            "labels": self._labels(caso.get("etiquetas", []) + ["k0lmenIA"]),
        }
        prioridad = self._id_por_nombre("priorities", set(PRIORIDADES.get(caso.get("prioridad"), [])))
        if prioridad:
            cuerpo["priority"] = prioridad
        if caso["tipo"] != "cucumber":
            cuerpo["steps"] = [{"stepDetails": p["accion"], "testData": p["datos"],
                                "expectedResult": p["resultado"]} for p in caso["pasos"]]
        r = self.http.post("/testcases", json_body=cuerpo)
        creado = {"key": r.get("key"), "id": r.get("id"), "versionNo": r.get("versionNo", 1)}
        if caso["tipo"] == "cucumber":
            self.http.put(f'/testcases/{creado["id"]}/versions/{creado["versionNo"]}',
                          json_body={"bddScenario": caso["gherkin"]})
        return creado

    def _link_jql(self, historia):
        return {"filter": {"jql": f"key in ('{historia}')"}}

    def vincular_caso_historia(self, caso, historia):
        c = self._caso(caso)
        r = self.http.post(f'/testcases/{c["id"]}/version/{c["versionNo"]}/requirements/link',
                           json_body=self._link_jql(historia))
        if isinstance(r, dict) and r.get("warningMessages"):
            raise ErrorGestion(f"QTM4J no vinculó {caso['key']} con {historia}: {r['warningMessages']}")

    # --- ciclos -------------------------------------------------------------------------
    def crear_ciclo(self, nombre, descripcion="", carpeta_ruta=None):
        cuerpo = {"projectId": self.project_id, "summary": nombre[:255], "description": descripcion}
        if carpeta_ruta:
            cuerpo["folderId"] = self._carpeta("testcycle-folders", carpeta_ruta)
        r = self.http.post("/testcycles", json_body=cuerpo)
        return {"key": r.get("key"), "id": r.get("id")}

    def vincular_ciclo_historia(self, ciclo, historia):
        self.http.post(f"/testcycles/{self._ciclo_id(ciclo)}/requirements/link", json_body=self._link_jql(historia))

    def agregar_casos_ciclo(self, ciclo, casos):
        ciclo_id = self._ciclo_id(ciclo)
        resueltos = [self._caso(c) for c in casos]
        for i in range(0, len(resueltos), 100):
            self.http.post(f"/testcycles/{ciclo_id}/testcases", json_body={
                "testCases": [{"id": c["id"], "versionNo": c["versionNo"]} for c in resueltos[i:i + 100]]})

    # --- resultados ---------------------------------------------------------------------
    def _ejecucion_id(self, ciclo_id, caso):
        if self.dry_run:
            return "DRY-EXEC"
        inicio = 0
        while True:
            r = self.http.post(f"/testcycles/{ciclo_id}/testcases/search",
                               params={"startAt": inicio, "maxResults": 100}, json_body={"filter": {}})
            for item in r.get("data", []):
                if item.get("key") == caso["key"]:
                    return item.get("testCaseExecutionId")
            inicio += 100
            if inicio >= r.get("total", 0):
                return None

    def registrar_resultado(self, ciclo, caso, estado, comentario, evidencias):
        ciclo_id = self._ciclo_id(ciclo)
        ejecucion = self._ejecucion_id(ciclo_id, caso)
        if ejecucion is None:  # el caso no estaba en el ciclo: se agrega y se vuelve a buscar
            self.agregar_casos_ciclo({**ciclo, "id": ciclo_id}, [caso])
            ejecucion = self._ejecucion_id(ciclo_id, caso)
        if ejecucion is None:
            raise ErrorGestion(f"No encuentro la ejecución de {caso['key']} en {ciclo['key']}.")
        resultado_id = self._id_por_nombre("execution-results", {self.estados[estado].lower()}, campo="defaultName") \
            or self._id_por_nombre("execution-results", {self.estados[estado].lower()})
        if resultado_id is None and not self.dry_run:
            raise ErrorGestion(f"QTM4J no tiene el resultado '{self.estados[estado]}' (configurable con QTM4J_ESTADOS).")
        self.http.put(f"/testcycles/{ciclo_id}/testcase-executions/{ejecucion}",
                      json_body={"executionResultId": resultado_id, "comment": comentario[:30000]})
        no_subidas = []
        for archivo in evidencias:
            ruta = Path(archivo)
            try:
                firmada = self.http.get(f"/testcycles/{ciclo_id}/testcase-executions/attachments/url",
                                        params={"projectId": self.project_id, "fileName": ruta.name,
                                                "testcaseExecutionId": ejecucion})
                if self.dry_run:
                    print(f"[dry-run] S3 POST (multipart) {ruta.name}")
                    continue
                requests = necesitar("requests")
                with open(ruta, "rb") as f:
                    s3 = requests.post(firmada["endpoint_url"], data=firmada["params"],
                                       files={"file": (ruta.name, f)}, timeout=300)
                if s3.status_code not in (200, 201, 204):
                    no_subidas.append((archivo, f"S3 respondió {s3.status_code}"))
            except ErrorGestion as e:
                no_subidas.append((archivo, str(e)[:200]))
        return no_subidas
