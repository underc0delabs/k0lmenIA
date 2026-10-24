#!/usr/bin/env python3
"""
Inventario de QA de una org de Salesforce AUTORIZADA (sandbox o scratch), con la CLI oficial `sf`.

Uso (desde la raíz del repo):
    python herramientas/salesforce/inventario.py --org <alias> [--objetos Account,Opportunity,Pedido__c]
        [--historia HU-001] [--apex] [--permitir-produccion] [--confirmar]

Qué hace (solo lectura, salvo --apex):
- Verifica que el alias esté en SALESFORCE_ORGS_AUTORIZADAS del .env y que la org esté conectada (sf org display).
- Lee la org (Organization: si es sandbox, tipo, idioma, zona horaria). Si es PRODUCCIÓN, corta salvo
  --permitir-produccion (y aun así, solo lectura y sin --apex).
- Releva lo que hay que probar: perfiles y usuarios activos por perfil (solo conteos), permission sets,
  record types, reglas de validación (Tooling API), flows (con los Process Builder que quedaron activos),
  triggers de Apex, cobertura de Apex (ApexCodeCoverageAggregate), modelo de sharing (OWD) de los objetos,
  reglas de duplicados, procesos de aprobación y límites de la org (sf org list limits).
- Con --apex corre los tests de Apex locales (RunLocalTests) con cobertura: no deja datos (Apex revierte lo
  que crean sus tests), pero consume límites asíncronos; por eso se confirma y nunca corre en producción.
- Calcula hallazgos (cobertura < 75 %, tests fallidos, límites casi agotados, Process Builder activos,
  varios triggers por objeto, OWD públicos de lectura/escritura, reglas inactivas) y sugerencias de prueba
  (un negativo por regla de validación, una prueba por flow disparado por registro, bulk de 200 por trigger,
  una por perfil con usuarios).
- Deja en output/salesforce/<historia o alias>/: salesforce.json e informe-salesforce.html; la corrida
  anterior pasa a historial/ (últimas 5).

Las consultas se pasan a `sf` por archivo (--file), así nada se interpreta en la línea de comandos.
No crea, edita ni borra registros, metadata, usuarios ni permisos.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
PROYECTO = Path(os.environ.get("K0LMENIA_PROYECTO") or RAIZ).resolve()  # datos del proyecto (scripts/_proyecto.py)
COBERTURA_MINIMA = 75  # la que exige Salesforce para desplegar a producción
OBJETOS_ESTANDAR = ["Account", "Contact", "Lead", "Opportunity", "Case"]
LIMITES_CLAVE = {"DailyApiRequests", "DataStorageMB", "FileStorageMB", "DailyAsyncApexExecutions",
                 "DailyBulkV2QueryJobs", "DailyWorkflowEmails", "SingleEmail", "MassEmail", "HourlyPublishedPlatformEvents"}
OWD_ABIERTOS = {"ReadWrite", "ReadWriteTransfer", "FullAccess"}

CONSULTAS = {
    "organizacion": ("SELECT Id, Name, OrganizationType, IsSandbox, InstanceName, LanguageLocaleKey, TimeZoneSidKey "
                     "FROM Organization", False),
    "perfiles": ("SELECT Id, Name, UserType FROM Profile ORDER BY Name", False),
    "usuarios_por_perfil": ("SELECT Profile.Name, COUNT(Id) total FROM User WHERE IsActive = true GROUP BY Profile.Name", False),
    "permission_sets": ("SELECT Name, Label, NamespacePrefix FROM PermissionSet WHERE IsOwnedByProfile = false ORDER BY Label", False),
    "record_types": ("SELECT SobjectType, DeveloperName, Name, IsActive FROM RecordType ORDER BY SobjectType", False),
    "validaciones": ("SELECT Id, ValidationName, Active, ErrorDisplayField, ErrorMessage, EntityDefinition.QualifiedApiName "
                     "FROM ValidationRule", True),
    "flows": ("SELECT ApiName, Label, ProcessType, TriggerType, IsActive, LastModifiedDate FROM FlowDefinitionView ORDER BY Label", False),
    "triggers": ("SELECT Name, TableEnumOrId, Status FROM ApexTrigger WHERE NamespacePrefix = null ORDER BY TableEnumOrId", False),
    "cobertura": ("SELECT ApexClassOrTrigger.Name, NumLinesCovered, NumLinesUncovered FROM ApexCodeCoverageAggregate", True),
    "objetos_custom": ("SELECT DeveloperName, NamespacePrefix FROM CustomObject", True),
    "duplicados": ("SELECT DeveloperName, SobjectType, IsActive FROM DuplicateRule", False),
    "aprobaciones": ("SELECT Name, TableEnumOrId, State FROM ProcessDefinition WHERE Type = 'Approval'", False),
}


def salir(msg, codigo=2):
    print(msg, file=sys.stderr)
    sys.exit(codigo)


def leer_env():
    sys.path.insert(0, str(RAIZ / "scripts"))
    from _env import leer_env as _leer
    valores = _leer()
    valores.update({k: v for k, v in os.environ.items() if k.startswith("SALESFORCE_")})
    return valores


def autorizada(alias, env):
    lista = [u.strip() for u in re.split(r"[,\s]+", env.get("SALESFORCE_ORGS_AUTORIZADAS", "")) if u.strip()]
    if not lista:
        salir("No hay orgs de Salesforce autorizadas. Agregá en el .env de la raíz:\n"
              "  SALESFORCE_ORGS_AUTORIZADAS=mi-sandbox-qa\n"
              "(el alias con el que la autorizaste: sf org login web --alias mi-sandbox-qa --instance-url https://test.salesforce.com).")
    if alias not in lista:
        salir(f"{alias} no está en SALESFORCE_ORGS_AUTORIZADAS del .env. Solo se relevan orgs autorizadas.")


def cli_sf():
    sf = shutil.which("sf")
    if not sf:
        salir("No se encontró la CLI de Salesforce (sf). Instalala con: npm install --global @salesforce/cli\n"
              "y autorizá la org: sf org login web --alias <alias> --instance-url https://test.salesforce.com")
    return sf


def correr_sf(sf, args, timeout=180):
    """Corre `sf <args> --json` y devuelve (result, error). sf contesta JSON con status 0 si salió bien."""
    try:
        p = subprocess.run([sf, *args, "--json"], capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    except subprocess.TimeoutExpired:
        return None, f"sf {args[0]} {args[1] if len(args) > 1 else ''}: tardó más de {timeout} s"
    try:
        datos = json.loads(p.stdout or "{}")
    except ValueError:
        return None, (p.stderr or p.stdout or "respuesta no JSON").strip()[:300]
    if datos.get("status", 1) != 0:
        return None, (datos.get("message") or datos.get("name") or "error de sf").strip()[:300]
    return datos.get("result"), None


def consultar(sf, alias, soql, tooling=False):
    """SOQL de solo lectura por archivo (--file): devuelve (registros, error)."""
    with tempfile.NamedTemporaryFile("w", suffix=".soql", delete=False, encoding="utf-8") as f:
        f.write(soql)
        ruta = f.name
    try:
        args = ["data", "query", "--file", ruta, "--target-org", alias]
        if tooling:
            args.append("--use-tooling-api")
        res, err = correr_sf(sf, args)
    finally:
        os.unlink(ruta)
    if err:
        return [], err
    return [{k: v for k, v in r.items() if k != "attributes"} for r in (res or {}).get("records", [])], None


def _nombre_rel(r, rel, campo="Name"):
    v = r.get(rel)
    return v.get(campo) if isinstance(v, dict) else r.get(campo)


def objetos_a_revisar(pedidos, custom):
    if pedidos:
        return [o.strip() for o in pedidos.split(",") if re.fullmatch(r"[A-Za-z][\w]*", o.strip())][:50]
    nombres = [f'{c["NamespacePrefix"] + "__" if c.get("NamespacePrefix") else ""}{c["DeveloperName"]}__c'
               for c in custom if c.get("DeveloperName")]
    return (OBJETOS_ESTANDAR + sorted(nombres))[:50]


def hallazgos_y_sugerencias(inv):
    h, s = [], []
    org = inv.get("organizacion") or {}
    if org and not org.get("IsSandbox"):
        h.append({"severidad": "Crítica", "area": "Org", "texto": "La org es de PRODUCCIÓN: se relevó en solo lectura y no se corrió Apex."})

    cob = inv.get("cobertura") or []
    cubiertas = sum(c.get("NumLinesCovered") or 0 for c in cob)
    sin_cubrir = sum(c.get("NumLinesUncovered") or 0 for c in cob)
    if cubiertas + sin_cubrir:
        pct = 100 * cubiertas / (cubiertas + sin_cubrir)
        inv["cobertura_org"] = round(pct, 1)
        if pct < COBERTURA_MINIMA:
            h.append({"severidad": "Alta", "area": "Apex",
                      "texto": f"Cobertura de Apex de la org {pct:.1f} %: menos del {COBERTURA_MINIMA} % que exige Salesforce para desplegar a producción."})
        ceros = sorted(_nombre_rel(c, "ApexClassOrTrigger") or "?" for c in cob
                       if not c.get("NumLinesCovered") and (c.get("NumLinesUncovered") or 0) > 0)
        if ceros:
            h.append({"severidad": "Media", "area": "Apex",
                      "texto": f"{len(ceros)} clase(s) o trigger(s) sin ninguna línea cubierta: {', '.join(ceros[:10])}{'…' if len(ceros) > 10 else ''}."})
    elif not inv.get("errores", {}).get("cobertura"):
        h.append({"severidad": "Baja", "area": "Apex", "texto": "No hay datos de cobertura (nunca se corrieron los tests de Apex o no hay Apex propio)."})

    apex = inv.get("apex") or {}
    for t in apex.get("fallidos") or []:
        h.append({"severidad": "Alta", "area": "Apex", "texto": f'Test de Apex fallido: {t.get("nombre")} — {(t.get("mensaje") or "")[:200]}'})

    for lim in inv.get("limites") or []:
        maximo, queda = lim.get("max") or 0, lim.get("remaining")
        if lim.get("name") in LIMITES_CLAVE and maximo and queda is not None:
            usado = 100 * (maximo - queda) / maximo
            if usado >= 80:
                h.append({"severidad": "Alta" if usado >= 90 else "Media", "area": "Límites",
                          "texto": f'{lim["name"]}: usado el {usado:.0f} % ({maximo - queda} de {maximo}). Las pruebas pueden fallar por límite y no por un bug.'})

    for f in inv.get("flows") or []:
        if f.get("IsActive") and f.get("ProcessType") == "Workflow":
            h.append({"severidad": "Media", "area": "Automatización",
                      "texto": f'Process Builder activo "{f.get("Label")}": Salesforce lo retiró (fin de soporte 2025-12-31); conviene migrarlo a Flow y probar el reemplazo.'})
        if f.get("IsActive") and f.get("TriggerType") in ("RecordBeforeSave", "RecordAfterSave", "RecordBeforeDelete"):
            s.append({"area": "Flow", "elemento": f.get("Label") or f.get("ApiName"),
                      "prueba": f'Crear/editar el registro que dispara "{f.get("Label")}" ({f.get("TriggerType")}) y verificar sus efectos, también en carga masiva (200 registros).'})
        elif f.get("IsActive") and f.get("ProcessType") == "Flow":
            s.append({"area": "Flow", "elemento": f.get("Label") or f.get("ApiName"),
                      "prueba": f'Recorrer el screen flow "{f.get("Label")}" por cada camino de decisión, con datos válidos e inválidos.'})

    por_objeto = {}
    for t in inv.get("triggers") or []:
        if t.get("Status") == "Active":
            por_objeto.setdefault(t.get("TableEnumOrId"), []).append(t.get("Name"))
            s.append({"area": "Apex", "elemento": t.get("Name"),
                      "prueba": f'Insertar/actualizar 200 registros de {t.get("TableEnumOrId")} de una vez (bulk) y verificar que el trigger {t.get("Name")} no supere límites de gobierno.'})
        elif t.get("Status") == "Inactive":
            h.append({"severidad": "Baja", "area": "Apex", "texto": f'Trigger inactivo {t.get("Name")} en {t.get("TableEnumOrId")}: confirmar si debería estar activo.'})
    for obj, nombres in por_objeto.items():
        if len(nombres) > 1:
            h.append({"severidad": "Media", "area": "Apex",
                      "texto": f'{obj} tiene {len(nombres)} triggers activos ({", ".join(nombres)}): Salesforce no garantiza su orden de ejecución.'})

    for v in inv.get("validaciones") or []:
        obj = _nombre_rel(v, "EntityDefinition", "QualifiedApiName")
        if v.get("Active"):
            s.append({"area": "Validación", "elemento": f'{obj}.{v.get("ValidationName")}',
                      "prueba": f'Guardar un {obj} que rompa la regla y verificar el mensaje "{(v.get("ErrorMessage") or "")[:120]}"'
                                f'{" en el campo " + v["ErrorDisplayField"] if v.get("ErrorDisplayField") else " arriba del formulario"}; y uno que la cumpla.'})
        else:
            h.append({"severidad": "Baja", "area": "Validación", "texto": f'Regla de validación inactiva {obj}.{v.get("ValidationName")}: confirmar si es intencional.'})

    for o in inv.get("sharing") or []:
        if o.get("InternalSharingModel") in OWD_ABIERTOS:
            h.append({"severidad": "Media", "area": "Sharing",
                      "texto": f'{o.get("QualifiedApiName")}: acceso por defecto interno "{o.get("InternalSharingModel")}" (todos ven y editan). Confirmar que es lo esperado.'})
        if o.get("InternalSharingModel") in ("Private", "Read"):
            s.append({"area": "Sharing", "elemento": o.get("QualifiedApiName"),
                      "prueba": f'Con un usuario que no es dueño ni está arriba en la jerarquía de roles, verificar que no pueda {"ver" if o.get("InternalSharingModel") == "Private" else "editar"} un {o.get("QualifiedApiName")} ajeno.'})

    for d in inv.get("duplicados") or []:
        if not d.get("IsActive"):
            h.append({"severidad": "Baja", "area": "Datos", "texto": f'Regla de duplicados inactiva {d.get("SobjectType")}.{d.get("DeveloperName")}.'})
        else:
            s.append({"area": "Datos", "elemento": f'{d.get("SobjectType")}.{d.get("DeveloperName")}',
                      "prueba": f'Crear un {d.get("SobjectType")} duplicado y verificar que se bloquee o se avise según la regla.'})

    for a in inv.get("aprobaciones") or []:
        if a.get("State") == "Active":
            s.append({"area": "Aprobación", "elemento": a.get("Name"),
                      "prueba": f'Enviar a aprobación un {a.get("TableEnumOrId")} y recorrer aprobar, rechazar y recuperar, verificando bloqueo del registro y notificaciones.'})

    for p in inv.get("usuarios_por_perfil") or []:
        nombre = _nombre_rel(p, "Profile")
        if nombre and (p.get("total") or 0) > 0:
            s.append({"area": "Permisos", "elemento": nombre,
                      "prueba": f'Con un usuario de prueba del perfil "{nombre}", verificar qué objetos, campos, pestañas y botones ve y puede usar (probador-permisos).'})

    rts = {}
    for r in inv.get("record_types") or []:
        if r.get("IsActive"):
            rts.setdefault(r.get("SobjectType"), []).append(r.get("Name"))
    for obj, nombres in rts.items():
        if len(nombres) > 1:
            s.append({"area": "Record types", "elemento": obj,
                      "prueba": f'Crear un {obj} con cada record type ({", ".join(nombres)}) y verificar layout, picklists y validaciones de cada uno.'})

    orden = {"Crítica": 0, "Alta": 1, "Media": 2, "Baja": 3}
    h.sort(key=lambda x: orden.get(x["severidad"], 9))
    return h, s


def correr_apex(sf, alias):
    res, err = correr_sf(sf, ["apex", "run", "test", "--test-level", "RunLocalTests", "--code-coverage",
                              "--result-format", "json", "--wait", "30", "--target-org", alias], timeout=1900)
    if err:
        return {"error": err}
    res = res or {}
    resumen = res.get("summary") or {}
    fallidos = [{"nombre": t.get("FullName") or f'{(t.get("ApexClass") or {}).get("Name", "?")}.{t.get("MethodName", "?")}',
                 "mensaje": t.get("Message") or ""} for t in res.get("tests") or [] if t.get("Outcome") not in ("Pass", "Skip")]
    return {"resultado": resumen.get("outcome"), "corridos": resumen.get("testsRan"), "aprobados": resumen.get("passing"),
            "fallidos_n": resumen.get("failing"), "cobertura_org": resumen.get("orgWideCoverage"), "fallidos": fallidos}


def main(argv=None):
    for flujo in (sys.stdout, sys.stderr):
        flujo.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Inventario de QA de una org de Salesforce (solo lectura).")
    ap.add_argument("--org", help="alias de la org autorizada en sf (o SALESFORCE_ORG del .env)")
    ap.add_argument("--objetos", default="", help="objetos para el modelo de sharing, separados por coma (o SALESFORCE_OBJETOS)")
    ap.add_argument("--historia", default="")
    ap.add_argument("--apex", action="store_true", help="correr los tests de Apex locales con cobertura (nunca en producción)")
    ap.add_argument("--permitir-produccion", action="store_true", help="relevar una org de producción en solo lectura")
    ap.add_argument("--confirmar", action="store_true")
    args = ap.parse_args(argv)

    env = leer_env()
    alias = args.org or env.get("SALESFORCE_ORG") or ""
    if not alias:
        salir("Falta la org: pasala con --org <alias> o poné SALESFORCE_ORG en el .env.")
    if not re.fullmatch(r"[\w.@+-]+", alias):
        salir(f"Alias inválido: {alias!r}")
    autorizada(alias, env)
    sf = cli_sf()

    if not args.confirmar:
        print(f"Vas a relevar la org {alias} de Salesforce (solo lectura{'; además se corren los tests de Apex' if args.apex else ''}).")
        if input("¿Confirmás? [s/N] ").strip().lower() not in ("s", "si", "sí", "y", "yes"):
            salir("Cancelado.", 1)

    print(f"[salesforce] Conectando con {alias} …", file=sys.stderr)
    info, err = correr_sf(sf, ["org", "display", "--target-org", alias])
    if err:
        salir(f"No se pudo conectar con la org {alias}: {err}\nAutorizala con: sf org login web --alias {alias} --instance-url https://test.salesforce.com")
    orgs, err = consultar(sf, alias, CONSULTAS["organizacion"][0])
    if err or not orgs:
        salir(f"No se pudo leer la organización: {err or 'sin datos'}")
    org = orgs[0]
    if not org.get("IsSandbox"):
        if not args.permitir_produccion:
            salir(f"La org {alias} es de PRODUCCIÓN ({org.get('OrganizationType')}). No se releva sin --permitir-produccion "
                  "(y la autorización explícita de su responsable). Usá un sandbox.")
        if args.apex:
            salir("En producción no se corren tests de Apex. Sacá --apex.")

    inv = {"organizacion": org, "errores": {}}
    for clave, (soql, tooling) in CONSULTAS.items():
        if clave in ("organizacion", "objetos_custom"):
            continue
        print(f"[salesforce] {clave} …", file=sys.stderr)
        registros, err = consultar(sf, alias, soql, tooling)
        inv[clave] = registros
        if err:
            inv["errores"][clave] = err
    custom, err = consultar(sf, alias, CONSULTAS["objetos_custom"][0], True)
    if err:
        inv["errores"]["objetos_custom"] = err
    inv["objetos_custom"] = custom
    objetos = objetos_a_revisar(args.objetos or env.get("SALESFORCE_OBJETOS", ""), custom)
    lista = ", ".join(f"'{o}'" for o in objetos)
    inv["sharing"], err = consultar(sf, alias, "SELECT QualifiedApiName, Label, InternalSharingModel, ExternalSharingModel "
                                               f"FROM EntityDefinition WHERE QualifiedApiName IN ({lista})")
    if err:
        inv["errores"]["sharing"] = err
    limites, err = correr_sf(sf, ["org", "list", "limits", "--target-org", alias])
    inv["limites"] = limites or []
    if err:
        inv["errores"]["limites"] = err
    if args.apex:
        print("[salesforce] Corriendo los tests de Apex (puede tardar varios minutos) …", file=sys.stderr)
        inv["apex"] = correr_apex(sf, alias)
        if inv["apex"].get("error"):
            inv["errores"]["apex"] = inv["apex"]["error"]

    hallazgos, sugerencias = hallazgos_y_sugerencias(inv)
    datos = {"generado": datetime.datetime.now().isoformat(timespec="seconds"), "historia": args.historia or None,
             "org": {"alias": alias, "nombre": org.get("Name"), "tipo": org.get("OrganizationType"), "sandbox": bool(org.get("IsSandbox")),
                     "instancia": org.get("InstanceName"), "idioma": org.get("LanguageLocaleKey"), "zona_horaria": org.get("TimeZoneSidKey"),
                     "api": (info or {}).get("apiVersion"), "url": (info or {}).get("instanceUrl")},
             "inventario": inv, "hallazgos": hallazgos, "sugerencias": sugerencias}

    carpeta = PROYECTO / "output" / "salesforce" / re.sub(r"[^\w.-]+", "-", args.historia or alias)
    carpeta.mkdir(parents=True, exist_ok=True)
    try:
        sys.path.insert(0, str(RAIZ / "scripts"))
        import _historial
        _historial.archivar(carpeta, ["salesforce.json", "analisis.json", "informe-salesforce.html"], "salesforce.json")
    except Exception as ex:
        print(f"[aviso] no se pudo archivar la corrida anterior: {ex}", file=sys.stderr)
    (carpeta / "salesforce.json").write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        import generar_informe_salesforce
        generar_informe_salesforce.generar(carpeta / "salesforce.json", carpeta / "informe-salesforce.html")
        print(f"[salesforce] Informe: {carpeta / 'informe-salesforce.html'}", file=sys.stderr)
    except Exception as ex:
        print(f"[aviso] no se pudo generar el informe HTML: {ex}", file=sys.stderr)
    print(f"[salesforce] {len(hallazgos)} hallazgo(s), {len(sugerencias)} sugerencia(s) de prueba"
          f"{', ' + str(len(inv['errores'])) + ' consulta(s) con error' if inv['errores'] else ''}.")
    print(f"[salesforce] Datos: {carpeta / 'salesforce.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
