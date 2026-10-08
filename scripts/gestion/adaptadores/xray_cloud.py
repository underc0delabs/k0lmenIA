"""Xray Cloud: GraphQL v2 (+ REST v2 para autenticar) y Jira Cloud REST para los vínculos.

Docs: https://docs.getxray.app/display/XRAYCLOUD/GraphQL+API
      https://us.xray.cloud.getxray.app/doc/graphql/

Mapeo:
- carpeta  -> carpeta del Test Repository (se identifica por ruta, ej. "/HU-001/Registro")
- caso     -> issue "Test" (Manual con pasos o Cucumber con gherkin)
- ciclo    -> issue "Test Execution"
- vínculo caso-historia  -> issue link de Jira tipo "Test" (cobertura de Xray)
- vínculo ciclo-historia -> issue link de Jira tipo "Relates" (Xray no define cobertura para ejecuciones)
"""
import base64
import json
import os
from pathlib import Path

from adaptadores.base import Adaptador, titulo_remoto
from comun import ErrorGestion, Http, env

ESTADOS = {
    "aprobado": "PASSED", "fallido": "FAILED", "pendiente": "TODO",
    "en_ejecucion": "EXECUTING", "bloqueado": "ABORTED",
}
PRIORIDADES = {"Crítica": "Highest", "Alta": "High", "Media": "Medium", "Baja": "Low"}


class XrayCloud(Adaptador):
    nombre = "xray-cloud"

    def __init__(self, proyecto, dry_run=False):
        super().__init__(proyecto, dry_run)
        base = env("XRAY_CLOUD_URL", obligatoria=False, defecto="https://xray.cloud.getxray.app")
        self.xray = Http(base, dry_run=dry_run, nombre="xray")
        self.estados = {**ESTADOS, **json.loads(os.environ.get("XRAY_ESTADOS", "{}") or "{}")}
        self.prioridades = {**PRIORIDADES, **json.loads(os.environ.get("GESTION_PRIORIDADES", "{}") or "{}")}
        self.tipo_link_caso = env("XRAY_LINK_CASO", obligatoria=False, defecto="Test")
        self.tipo_link_ciclo = env("XRAY_LINK_CICLO", obligatoria=False, defecto="Relates")
        self._jira = None
        self._project_id = None
        self._ids = {}
        if not dry_run:
            token = self.xray.post("/api/v2/authenticate", json_body={
                "client_id": env("XRAY_CLOUD_CLIENT_ID"), "client_secret": env("XRAY_CLOUD_CLIENT_SECRET")})
            token = token if isinstance(token, str) else token.get("texto", "").strip('"')
            self.xray.headers["Authorization"] = f"Bearer {token}"

    # --- utilidades ------------------------------------------------------------
    def gql(self, consulta, variables=None):
        if self.dry_run:
            print(f"[dry-run] xray GraphQL {' '.join(consulta.split())[:300]} vars={json.dumps(variables or {}, ensure_ascii=False)[:400]}")
            return {}
        r = self.xray.post("/api/v2/graphql", json_body={"query": consulta, "variables": variables or {}})
        if r.get("errors"):
            raise ErrorGestion("Xray GraphQL: " + "; ".join(e.get("message", "") for e in r["errors"]))
        return r.get("data") or {}

    @property
    def jira(self):
        """Jira Cloud REST (email + API token): solo para los issue links."""
        if self._jira is None and self.dry_run:
            self._jira = Http("https://jira.dry-run", dry_run=True, nombre="jira")
        if self._jira is None:
            token = base64.b64encode(f'{env("JIRA_EMAIL")}:{env("JIRA_API_TOKEN")}'.encode()).decode()
            self._jira = Http(env("JIRA_BASE_URL"), {"Authorization": f"Basic {token}"},
                              dry_run=self.dry_run, nombre="jira")
        return self._jira

    @property
    def project_id(self):
        if self._project_id is None:
            if self.dry_run:
                self._project_id = "DRY-PROJECT"
            else:
                d = self.gql("query($p:String){ getProjectSettings(projectIdOrKey:$p){ projectId } }",
                             {"p": self.proyecto})
                self._project_id = (d.get("getProjectSettings") or {}).get("projectId")
                if not self._project_id:
                    raise ErrorGestion(f"Xray no encuentra el proyecto {self.proyecto}.")
        return self._project_id

    def issue_id(self, item):
        """Las mutations de Xray piden el id numérico del issue; lo resolvemos desde la key."""
        if item.get("id") and not str(item["id"]).startswith("DRY"):
            return str(item["id"])
        key = item["key"]
        if self.dry_run:
            return f"id({key})"
        if key not in self._ids:
            r = self.jira.get(f"/rest/api/3/issue/{key}", params={"fields": "id"})
            self._ids[key] = str(r["id"])
        return self._ids[key]

    def _link(self, tipo, origen_key, destino_key):
        """Issue link de Jira. Con XRAY_LINK_INVERTIR=1 se invierte el sentido si en tu
        Jira el vínculo queda al revés (la historia tiene que mostrar 'is tested by')."""
        inward, outward = origen_key, destino_key
        if os.environ.get("XRAY_LINK_INVERTIR", "").strip() in ("1", "true", "on"):
            inward, outward = outward, inward
        self.jira.post("/rest/api/3/issueLink", json_body={
            "type": {"name": tipo}, "inwardIssue": {"key": inward}, "outwardIssue": {"key": outward}})

    # --- repositorio --------------------------------------------------------------
    def crear_carpeta(self, ruta):
        partes = [p for p in ruta.strip("/").split("/") if p]
        actual = ""
        for parte in partes:
            actual += "/" + parte
            existe = False
            if not self.dry_run:
                try:
                    d = self.gql("query($p:String,$r:String!){ getFolder(projectId:$p, path:$r){ path } }",
                                 {"p": self.project_id, "r": actual})
                    existe = bool((d.get("getFolder") or {}).get("path"))
                except ErrorGestion:
                    existe = False
            if not existe:
                try:
                    self.gql("mutation($p:String,$r:String!){ createFolder(projectId:$p, path:$r){ folder{ path } warnings } }",
                             {"p": self.project_id, "r": actual})
                except ErrorGestion as e:
                    if "exist" not in str(e).lower():
                        raise
        return "/" + "/".join(partes)

    def crear_caso(self, caso, carpeta_id, carpeta_ruta):
        descripcion = caso.get("descripcion", "")
        if caso.get("precondiciones"):
            descripcion += f"\n\nPrecondiciones: {caso['precondiciones']}"
        fields = {
            "summary": titulo_remoto(caso, 250),
            "project": {"key": self.proyecto},
            "description": descripcion.strip() or caso["titulo"],
            "labels": [e.replace(" ", "_") for e in caso.get("etiquetas", [])] + ["k0lmenIA"],
        }
        prioridad = self.prioridades.get(caso.get("prioridad"))
        if prioridad and os.environ.get("GESTION_ENVIAR_PRIORIDAD", "1") != "0":
            fields["priority"] = {"name": prioridad}
        if caso["tipo"] == "cucumber":
            consulta = ("mutation($j:JSON!,$g:String,$f:String){ createTest(testType:{name:\"Cucumber\"}, "
                        "gherkin:$g, folderPath:$f, jira:$j){ test{ issueId jira(fields:[\"key\"]) } warnings } }")
            variables = {"j": {"fields": fields}, "g": caso["gherkin"], "f": carpeta_ruta}
        else:
            pasos = [{"action": p["accion"], "data": p["datos"], "result": p["resultado"]} for p in caso["pasos"]]
            consulta = ("mutation($j:JSON!,$s:[CreateStepInput],$f:String){ createTest(testType:{name:\"Manual\"}, "
                        "steps:$s, folderPath:$f, jira:$j){ test{ issueId jira(fields:[\"key\"]) } warnings } }")
            variables = {"j": {"fields": fields}, "s": pasos, "f": carpeta_ruta}
        d = self.gql(consulta, variables)
        if self.dry_run:
            return {"key": f'DRY-{caso["id"]}', "id": None}
        test = d["createTest"]["test"]
        return {"key": test["jira"]["key"], "id": str(test["issueId"])}

    def vincular_caso_historia(self, caso, historia):
        self._link(self.tipo_link_caso, caso["key"], historia)

    # --- ciclos -------------------------------------------------------------------
    def crear_ciclo(self, nombre, descripcion="", carpeta_ruta=None):
        fields = {"summary": nombre, "project": {"key": self.proyecto}, "labels": ["k0lmenIA"]}
        if descripcion:
            fields["description"] = descripcion
        d = self.gql("mutation($j:JSON!){ createTestExecution(jira:$j){ testExecution{ issueId jira(fields:[\"key\"]) } warnings } }",
                     {"j": {"fields": fields}})
        if self.dry_run:
            return {"key": "DRY-CICLO", "id": None}
        te = d["createTestExecution"]["testExecution"]
        return {"key": te["jira"]["key"], "id": str(te["issueId"])}

    def vincular_ciclo_historia(self, ciclo, historia):
        self._link(self.tipo_link_ciclo, ciclo["key"], historia)

    def agregar_casos_ciclo(self, ciclo, casos):
        ids = [self.issue_id(c) for c in casos]
        for i in range(0, len(ids), 100):
            self.gql("mutation($e:String!,$t:[String]){ addTestsToTestExecution(issueId:$e, testIssueIds:$t){ addedTests warning } }",
                     {"e": self.issue_id(ciclo), "t": ids[i:i + 100]})

    # --- resultados -----------------------------------------------------------------
    def _test_run_id(self, ciclo, caso):
        consulta = "query($t:String,$e:String){ getTestRun(testIssueId:$t, testExecIssueId:$e){ id } }"
        variables = {"t": self.issue_id(caso), "e": self.issue_id(ciclo)}
        if self.dry_run:
            self.gql(consulta, variables)
            return "DRY-RUN"
        run = self.gql(consulta, variables).get("getTestRun")
        if not run:  # el caso no estaba en el ciclo: se agrega y se vuelve a buscar
            self.agregar_casos_ciclo(ciclo, [caso])
            run = self.gql(consulta, variables).get("getTestRun")
        if not run:
            raise ErrorGestion(f"No encuentro la ejecución de {caso['key']} en {ciclo['key']}.")
        return run["id"]

    def registrar_resultado(self, ciclo, caso, estado, comentario, evidencias):
        run_id = self._test_run_id(ciclo, caso)
        self.gql("mutation($i:String!,$s:String!){ updateTestRunStatus(id:$i, status:$s) }",
                 {"i": run_id, "s": self.estados[estado]})
        self.gql("mutation($i:String!,$c:String!){ updateTestRunComment(id:$i, comment:$c) }",
                 {"i": run_id, "c": comentario})
        no_subidas = []
        limite = float(os.environ.get("GESTION_LIMITE_ADJUNTO_MB", "0") or 0) * 1024 * 1024
        for archivo in evidencias:
            ruta = Path(archivo)
            if limite and ruta.stat().st_size > limite:
                no_subidas.append((archivo, f"supera {limite / 1048576:.0f} MB"))
                continue
            mime = {"png": "image/png", "gif": "image/gif", "webm": "video/webm", "mp4": "video/mp4"}.get(ruta.suffix.lstrip(".").lower(),
                                                                                     "application/octet-stream")
            datos = "<base64>" if self.dry_run else base64.b64encode(ruta.read_bytes()).decode()
            try:
                self.gql("mutation($i:String!,$e:[AttachmentDataInput]!){ addEvidenceToTestRun(id:$i, evidence:$e){ addedEvidence warnings } }",
                         {"i": run_id, "e": [{"filename": ruta.name, "mimeType": mime, "data": datos}]})
            except ErrorGestion as e:
                no_subidas.append((archivo, str(e)[:200]))
        return no_subidas
