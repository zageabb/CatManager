import csv
import io
import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Flask, flash, g, jsonify, redirect, render_template, request, session, url_for

from legacy_demo_data import LEGACY_DEMO_PANELS, LEGACY_MDF_CODES

CATEGORIES = [
    "Transformers",
    "Switchgear",
    "Current Transformers",
    "Civil Engineering",
    "Cables & Conductors",
    "Protection & Control",
    "Electrical Equipment",
    "Mechanical Components",
    "Services",
    "General Equipment",
]
BUSINESSES = ["GI", "GA", "GPQSS", "HVDC"]
REGION_LEVELS = ["Global", "Region", "HUB", "Country"]
FIELD_TYPES = ["number", "text", "dropdown", "date", "boolean", "stars", "multiselect_blocks"]
DEFAULT_MDF_CODES = [
    {"code": "3GF", "description": "Grid equipment"},
    {"code": "MDF-TR-001", "description": "Power Transformers"},
    {"code": "MDF-SG-001", "description": "High Voltage Switchgear"},
    {"code": "MDF-CT-001", "description": "Current Transformers"},
    {"code": "MDF-CE-001", "description": "Civil Engineering"},
]

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def load_mdf_catalogue():
    catalogue_path = Path(__file__).resolve().parent / "data" / "mdf_codes.json"
    if catalogue_path.exists():
        try:
            rows = json.loads(catalogue_path.read_text(encoding="utf-8"))
            merged = {m["code"]: dict(m) for m in DEFAULT_MDF_CODES}
            for row in rows:
                if row.get("code") and row.get("description"):
                    code = str(row["code"]).strip()
                    merged[code] = {"code": code, "description": str(row["description"]).strip()}
            return list(merged.values())
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return DEFAULT_MDF_CODES

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        SECRET_KEY=os.environ.get("CATMANAGER_SECRET_KEY", "dev-change-me"),
        DATABASE=os.environ.get("CATMANAGER_DATABASE", str(Path(app.instance_path) / "catmanager.sqlite")),
        SEED_DEMO=True,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    def get_db():
        if "db" not in g:
            g.db = sqlite3.connect(app.config["DATABASE"])
            g.db.row_factory = sqlite3.Row
        return g.db

    @app.teardown_appcontext
    def close_db(_error=None):
        db = g.pop("db", None)
        if db is not None:
            db.close()

    def init_db():
        db = get_db()
        db.executescript("""
        CREATE TABLE IF NOT EXISTS panels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            panel_id TEXT NOT NULL UNIQUE,
            panel_name TEXT NOT NULL,
            category TEXT NOT NULL,
            business TEXT NOT NULL,
            region_level TEXT NOT NULL,
            region_value TEXT NOT NULL DEFAULT '',
            owner TEXT NOT NULL,
            mdf_code TEXT NOT NULL,
            data_json TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS mdf_codes (
            code TEXT PRIMARY KEY,
            description TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS supplier_master (
            bpid TEXT PRIMARY KEY,
            supplier_name TEXT NOT NULL,
            address TEXT NOT NULL DEFAULT '',
            post_code TEXT NOT NULL DEFAULT '',
            address_source TEXT NOT NULL DEFAULT 'generated',
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_supplier_master_name ON supplier_master(supplier_name);
        CREATE TABLE IF NOT EXISTS field_templates (
            template_id TEXT PRIMARY KEY,
            field_name TEXT NOT NULL,
            field_type TEXT NOT NULL,
            options_json TEXT NOT NULL DEFAULT '[]',
            required INTEGER NOT NULL DEFAULT 0,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """)
        columns = {row[1] for row in db.execute("PRAGMA table_info(panels)").fetchall()}
        if "archived_at" not in columns:
            db.execute("ALTER TABLE panels ADD COLUMN archived_at TEXT")
        if "is_favourite" not in columns:
            db.execute("ALTER TABLE panels ADD COLUMN is_favourite INTEGER NOT NULL DEFAULT 0")
        ts = now_iso()
        for m in load_mdf_catalogue():
            db.execute(
                """INSERT INTO mdf_codes(code,description,active,created_at,updated_at)
                   VALUES(?,?,?,?,?)
                   ON CONFLICT(code) DO UPDATE SET description=excluded.description, updated_at=excluded.updated_at""",
                (m["code"], m["description"], 1, ts, ts),
            )
        # Reusable starting library; never overwrite user-customized templates.
        for tid, name, kind, options in (
            ("standard_mva", "Rated Power (MVA)", "number", []),
            ("standard_voltage", "Rated Voltage (kV)", "number", []),
            ("standard_cooling", "Cooling Type", "dropdown", ["ONAN", "ONAF", "OFAF", "ODAF"]),
            ("standard_approved", "Approved", "boolean", []),
            ("standard_quality_rating", "Supplier Quality Rating", "stars", []),
        ):
            db.execute(
                "INSERT OR IGNORE INTO field_templates(template_id,field_name,field_type,options_json,required,updated_at) VALUES(?,?,?,?,?,?)",
                (tid, name, kind, json.dumps(options), 0, ts),
            )
        db.commit()
        rows = db.execute("SELECT id,mdf_code,data_json FROM panels").fetchall()
        for row in rows:
            try:
                payload = json.loads(row["data_json"])
                core = payload.get("panel", {})
                changed = False
                if "mdfCodes" not in core:
                    lead = core.get("leadMdfCode") or core.get("mdfCode") or row["mdf_code"]
                    core["mdfCode"] = lead
                    core["leadMdfCode"] = lead
                    core["mdfCodes"] = [lead] if lead else []
                    changed = True
                if int(payload.get("schemaVersion", 1)) < 4 or "fieldGroups" not in core:
                    core.setdefault("fieldGroups", [])
                    for field in core.get("supplierFields", []):
                        field.setdefault("groupId", "")
                    payload["schemaVersion"] = 4
                    metadata = core.setdefault("metadata", {})
                    metadata["version"] = max(int(metadata.get("version", 1)), 5)
                    metadata.setdefault("schema4MigratedAt", ts)
                    changed = True
                if int(payload.get("schemaVersion", 1)) < 5:
                    core.setdefault("dashboardWidgets", [])
                    payload["schemaVersion"] = 5
                    core.setdefault("metadata", {})["version"] = max(int(core["metadata"].get("version", 1)), 5)
                    changed = True
                if changed:
                    db.execute("UPDATE panels SET data_json=? WHERE id=?", (json.dumps(payload), row["id"]))
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        db.commit()
        if app.config.get("SEED_DEMO") and db.execute("SELECT COUNT(*) FROM panels").fetchone()[0] == 0:
            seed_demo(db)

    def build_panel_payload(panel_id, panel_name, category, business, region_level, region_value, owner, mdf_codes, lead_mdf_code, field_groups, fields, suppliers, created_at=None, metadata=None):
        metadata = json.loads(json.dumps(metadata or {}))
        metadata.setdefault("createdAt", created_at or now_iso())
        metadata["updatedAt"] = now_iso()
        metadata["version"] = max(int(metadata.get("version", 1)), 5)
        metadata.setdefault("auditTrail", [])
        return {
            "schemaVersion": 5,
            "panel": {
                "panelId": panel_id,
                "panelName": panel_name,
                "category": category,
                "business": business,
                "region": {"level": region_level, "value": region_value},
                "panelOwner": {"name": owner},
                "mdfCode": lead_mdf_code,
                "leadMdfCode": lead_mdf_code,
                "mdfCodes": list(mdf_codes),
                "fieldGroups": field_groups,
                "supplierFields": fields,
                "dashboardWidgets": [],
                "suppliers": suppliers,
                "metadata": metadata,
            },
        }

    def seed_demo(db):
        ts = now_iso()
        for code, description in LEGACY_MDF_CODES.items():
            db.execute(
                """INSERT INTO mdf_codes(code,description,active,created_at,updated_at)
                   VALUES(?,?,0,?,?)
                   ON CONFLICT(code) DO NOTHING""",
                (code, description, ts, ts),
            )

        for panel_index, source in enumerate(LEGACY_DEMO_PANELS):
            suppliers = []
            for supplier_index, source_supplier in enumerate(source.get("suppliers", [])):
                supplier = json.loads(json.dumps(source_supplier))
                field_ids = {f.get("fieldId") for f in source.get("supplierFields", [])}
                if "qualification_status" in field_ids and not supplier.get("customFields",{}).get("qualification_status"):
                    demo_statuses = ["Qualified", "In review", "Not qualified"]
                    supplier.setdefault("customFields",{})["qualification_status"] = demo_statuses[
                        (panel_index + supplier_index) % len(demo_statuses)
                    ]
                if not supplier.get("address"):
                    supplier["address"], supplier["postCode"] = generic_supplier_address(supplier["supplierId"])
                supplier.setdefault("postCode", "")
                supplier.setdefault("masterLinked", False)
                suppliers.append(supplier)

            metadata = json.loads(json.dumps(source.get("metadata", {})))
            metadata["createdAt"] = ts
            metadata["demoQualificationGenerated"] = True
            payload = build_panel_payload(
                source["panelId"],
                source["panelName"],
                source["category"],
                source.get("business","GI"),
                source["region"]["level"],
                source["region"]["value"],
                source["panelOwner"]["name"],
                source["mdfCodes"],
                source["leadMdfCode"],
                source.get("fieldGroups",[]),
                source.get("supplierFields",[]),
                suppliers,
                ts,
                metadata,
            )
            db.execute(
                """INSERT INTO panels(
                       panel_id,panel_name,category,business,region_level,region_value,
                       owner,mdf_code,data_json,created_at,updated_at
                   ) VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    source["panelId"],
                    source["panelName"],
                    source["category"],
                    source.get("business","GI"),
                    source["region"]["level"],
                    source["region"]["value"],
                    source["panelOwner"]["name"],
                    source["leadMdfCode"],
                    json.dumps(payload),
                    ts,
                    ts,
                ),
            )
        db.commit()

    def row_to_panel(row):
        item = dict(row)
        item["data"] = json.loads(item.pop("data_json"))
        return item

    def get_panel_or_404(panel_id):
        row = get_db().execute("SELECT * FROM panels WHERE panel_id=?", (panel_id,)).fetchone()
        if row is None:
            from flask import abort
            abort(404)
        return row_to_panel(row)

    def slug_id(value):
        out = "".join(c.lower() if c.isalnum() else "_" for c in value).strip("_")
        while "__" in out:
            out = out.replace("__","_")
        return out or f"field_{uuid4().hex[:8]}"

    def parse_fields(raw):
        try:
            fields = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            raise ValueError("Custom field definition is not valid JSON.") from exc
        seen, clean = set(), []
        for index, field in enumerate(fields):
            name = str(field.get("fieldName","")).strip()
            ftype = str(field.get("type","text")).lower()
            if not name:
                raise ValueError("Every custom field needs a name.")
            if ftype not in FIELD_TYPES:
                raise ValueError(f"Unsupported field type: {ftype}")
            fid = str(field.get("fieldId") or "").strip() or slug_id(name)
            base, n = fid, 2
            while fid in seen:
                fid = f"{base}_{n}"
                n += 1
            seen.add(fid)
            options = field.get("options",[]) if ftype in ("dropdown", "multiselect_blocks") else []
            if ftype == "multiselect_blocks" and (not isinstance(options, list) or len(options) > 12 or not options):
                raise ValueError("Multi-select blocks need 1 to 12 options.")
            if ftype == "multiselect_blocks" and len(set(str(x).strip() for x in options)) != len(options):
                raise ValueError("Multi-select block options must be unique.")
            clean.append({"fieldId":fid,"fieldName":name,"type":ftype,"options":[str(x).strip() for x in options if str(x).strip()],"required":bool(field.get("required",False)),"groupId":str(field.get("groupId") or "").strip(),"order":index+1})
        return clean

    def parse_multiselect_value(field, values):
        allowed = field.get("options", [])
        selected = list(dict.fromkeys(values))
        if any(value not in allowed for value in selected):
            raise ValueError("Unknown selection in " + field["fieldName"])
        if field.get("required") and not selected:
            raise ValueError(field["fieldName"] + " requires at least one selection.")
        return selected

    def parse_dashboard_widgets(raw, fields):
        try:
            widgets = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            raise ValueError("Dashboard widgets must be valid JSON.") from exc
        if not isinstance(widgets, list) or len(widgets) > 6:
            raise ValueError("A panel supports up to six dashboard widgets.")
        valid_fields = {"supplierId", "supplierName"} | {f["fieldId"] for f in fields}
        valid_metrics = {"count", "count_where", "sum", "average", "minimum", "maximum",
                         "distinct", "percentage", "ratio"}
        clean = []
        for widget in widgets:
            if not isinstance(widget, dict):
                raise ValueError("Invalid dashboard widget.")
            title = str(widget.get("title", "")).strip()[:80]
            metric = str(widget.get("metric", "")).strip()
            field = str(widget.get("fieldId", "")).strip()
            other = str(widget.get("otherFieldId", "")).strip()
            if not title or metric not in valid_metrics:
                raise ValueError("Each widget requires a title and valid calculation.")
            if metric != "count" and field not in valid_fields:
                raise ValueError("Widget refers to an unknown supplier field.")
            if metric in ("ratio", "percentage") and other not in valid_fields:
                raise ValueError("Widget denominator refers to an unknown field.")
            clean.append({"widgetId": str(widget.get("widgetId") or uuid4().hex),
                          "title": title, "metric": metric, "fieldId": field,
                          "otherFieldId": other, "match": str(widget.get("match", ""))[:100],
                          "format": widget.get("format") if widget.get("format") in ("number","currency","percentage","stars") else "number",
                          "display": widget.get("display") if widget.get("display") in ("panel","supplier","both") else "panel"})
        return clean

    def calculate_dashboard_widgets(core):
        suppliers = core.get("suppliers", [])
        config = get_dashboard_config()
        base_currency = config["baseCurrency"]
        prefix = {"GBP": "£", "EUR": "€", "USD": "$"}.get(base_currency, base_currency + " ")
        def values(field_id):
            if field_id in ("supplierId", "supplierName"):
                return [supplier.get(field_id) for supplier in suppliers]
            return [supplier.get("customFields", {}).get(field_id) for supplier in suppliers]
        def numbers(field_id):
            out, excluded = [], 0
            for supplier in suppliers:
                value = supplier.get("customFields", {}).get(field_id)
                if isinstance(value, bool) or value in (None, ""):
                    continue
                if field_id == config["spendFieldId"]:
                    converted = convert_spend(value, supplier.get("customFields", {}).get(config["currencyFieldId"]), config)
                    if converted is None:
                        excluded += 1
                        continue
                    number = converted
                else:
                    try:
                        number = float(value)
                    except (TypeError, ValueError, OverflowError):
                        excluded += 1
                        continue
                if number == number and abs(number) != float("inf"):
                    out.append(number)
                else:
                    excluded += 1
            return out, excluded
        results = []
        for widget in core.get("dashboardWidgets", [])[:6]:
            if widget.get("display", "panel") not in ("panel", "both"):
                continue
            metric = widget.get("metric")
            fid = widget.get("fieldId", "")
            nums, excluded = numbers(fid) if metric in ("sum","average","minimum","maximum","ratio","percentage") else ([], 0)
            value = None
            if metric == "count":
                value = len(suppliers)
            elif metric == "count_where":
                target = widget.get("match", "").strip().lower()
                value = sum(str(v).lower() == target for v in values(fid) if v is not None)
            elif metric == "distinct":
                value = len({str(v) for v in values(fid) if v is not None and v != ""})
            elif metric == "sum":
                value = sum(nums)
            elif metric == "average":
                value = sum(nums)/len(nums) if nums else None
            elif metric == "minimum":
                value = min(nums) if nums else None
            elif metric == "maximum":
                value = max(nums) if nums else None
            elif metric in ("ratio", "percentage"):
                denominator_values, denominator_excluded = numbers(widget.get("otherFieldId", ""))
                excluded += denominator_excluded
                denominator = sum(denominator_values)
                if denominator:
                    value = sum(nums)/denominator * (100 if metric == "percentage" else 1)
            results.append({"title": widget.get("title", "Widget"), "value": value,
                            "metric": metric, "format": widget.get("format", "number"),
                            "currencyPrefix": prefix, "excluded": excluded})
        return results

    def calculate_supplier_widgets(core):
        """Evaluate KPI definitions against each supplier independently; never persist results."""
        config = get_dashboard_config()
        prefix = {"GBP": "£", "EUR": "€", "USD": "$"}.get(
            config["baseCurrency"], config["baseCurrency"] + " "
        )
        widgets = [w for w in core.get("dashboardWidgets", [])[:6]
                   if w.get("display", "panel") in ("supplier", "both")]
        rows = []
        for supplier in core.get("suppliers", []):
            custom = supplier.get("customFields", {})
            def raw(field_id):
                return supplier.get(field_id) if field_id in ("supplierId", "supplierName") else custom.get(field_id)
            def number(field_id):
                v = raw(field_id)
                if isinstance(v, bool) or v is None or v == "":
                    return None
                if field_id == config["spendFieldId"]:
                    n = convert_spend(v, custom.get(config["currencyFieldId"]), config)
                else:
                    try:
                        n = float(v)
                    except (ValueError, TypeError, OverflowError):
                        return None
                return n if n is not None and n == n and abs(n) != float("inf") else None
            values = []
            for w in widgets:
                metric = w["metric"]
                field_id = w.get("fieldId", "")
                n = number(field_id)
                result = None
                if metric == "count":
                    result = 1
                elif metric == "count_where":
                    v = raw(field_id)
                    result = int(v is not None and str(v).lower() == w.get("match", "").strip().lower())
                elif metric == "distinct":
                    v = raw(field_id)
                    result = int(v is not None and v != "")
                elif metric in ("sum", "average", "minimum", "maximum"):
                    result = n
                elif metric in ("ratio", "percentage"):
                    denominator = number(w.get("otherFieldId", ""))
                    if n is not None and denominator not in (None, 0):
                        result = n / denominator * (100 if metric == "percentage" else 1)
                values.append({"value": result, "metric": metric,
                               "format": w.get("format", "number"),
                               "currencyPrefix": prefix})
            rows.append(values)
        return widgets, rows

    def parse_field_groups(raw):
        try:
            groups = json.loads(raw or "[]")
        except json.JSONDecodeError as exc:
            raise ValueError("Field group definition is not valid JSON.") from exc
        seen, clean = set(), []
        for index, group in enumerate(groups):
            name = str(group.get("name","")).strip()
            if not name:
                raise ValueError("Every field group needs a name.")
            gid = str(group.get("groupId") or "").strip() or slug_id(name)
            base, n = gid, 2
            while gid in seen:
                gid = f"{base}_{n}"
                n += 1
            seen.add(gid)
            clean.append({"groupId":gid,"name":name,"order":index+1})
        return clean

    def migrate_panel_payload(payload):
        if not isinstance(payload, dict) or not isinstance(payload.get("panel"), dict):
            raise ValueError("JSON must contain a panel object.")
        data = json.loads(json.dumps(payload))
        version = int(data.get("schemaVersion", 1))
        if version > 5:
            raise ValueError(f"Unsupported schemaVersion {version}.")
        core = data["panel"]
        metadata = core.setdefault("metadata", {})
        metadata.setdefault("createdAt", now_iso())
        metadata.setdefault("updatedAt", now_iso())
        metadata.setdefault("auditTrail", [])
        if version < 3:
            lead = core.get("leadMdfCode") or core.get("mdfCode")
            core["leadMdfCode"] = lead
            core["mdfCode"] = lead
            core["mdfCodes"] = core.get("mdfCodes") or ([lead] if lead else [])
        if version < 4:
            core.setdefault("fieldGroups", [])
            for field in core.get("supplierFields", []):
                field.setdefault("groupId", "")
        if version < 5:
            core.setdefault("dashboardWidgets", [])
        data["schemaVersion"] = 5
        metadata["version"] = max(int(metadata.get("version", 1)), 5)
        required = ["panelId","panelName","category","business","region","panelOwner","fieldGroups","supplierFields","suppliers","leadMdfCode","mdfCodes"]
        if not all(k in core for k in required):
            missing = [k for k in required if k not in core]
            raise ValueError("JSON is missing required panel properties: " + ", ".join(missing))
        if not isinstance(core["region"], dict) or "level" not in core["region"]:
            raise ValueError("region must contain level and value.")
        if not isinstance(core["panelOwner"], dict):
            raise ValueError("panelOwner must be an object.")
        core["fieldGroups"] = parse_field_groups(json.dumps(core.get("fieldGroups",[])))
        core["supplierFields"] = parse_fields(json.dumps(core.get("supplierFields",[])))
        group_ids = {g["groupId"] for g in core["fieldGroups"]}
        unknown_groups = sorted({f["groupId"] for f in core["supplierFields"] if f.get("groupId") and f["groupId"] not in group_ids})
        if unknown_groups:
            if version < 4:
                for field in core["supplierFields"]:
                    if field.get("groupId") not in group_ids:
                        field["groupId"] = ""
            else:
                raise ValueError("Custom fields reference unknown field groups: " + ", ".join(unknown_groups))
        core["dashboardWidgets"] = parse_dashboard_widgets(json.dumps(core.get("dashboardWidgets", [])), core["supplierFields"])
        if not isinstance(core.get("suppliers"), list):
            raise ValueError("suppliers must be a list.")
        return data

    def persist_imported_panel(payload, replace_existing=False, audit_import=False):
        data = migrate_panel_payload(payload)
        core = data["panel"]
        panel_id = str(core["panelId"]).strip()
        if not panel_id:
            raise ValueError("panelId is required.")
        category = str(core["category"])
        business = str(core["business"])
        region = core["region"]
        region_level = str(region.get("level",""))
        region_value = str(region.get("value") or region_level)
        owner = str(core.get("panelOwner",{}).get("name") or "").strip()
        lead = str(core.get("leadMdfCode") or "").strip()
        selected_mdfs = [str(x).strip() for x in core.get("mdfCodes",[]) if str(x).strip()]
        if category not in CATEGORIES or business not in BUSINESSES or region_level not in REGION_LEVELS:
            raise ValueError("Imported panel contains invalid controlled values.")
        if not owner or not lead or lead not in selected_mdfs:
            raise ValueError("Imported panel needs an owner, selected MDFs, and a valid Lead MDF.")
        known_mdfs = {m["code"] for m in get_mdf_codes(include_inactive=True)}
        if any(code not in known_mdfs for code in selected_mdfs):
            raise ValueError("Imported panel contains MDF codes not present in the MDF master.")
        db = get_db()
        existing = db.execute("SELECT * FROM panels WHERE panel_id=?", (panel_id,)).fetchone()
        ts = now_iso()
        data["panel"]["metadata"]["updatedAt"] = ts
        if existing:
            if not replace_existing:
                raise ValueError("Panel already exists. Enable Replace existing to import over it.")
            existing_data = json.loads(existing["data_json"])
            old_trail = existing_data.get("panel",{}).get("metadata",{}).get("auditTrail",[])
            incoming_trail = data["panel"].setdefault("metadata",{}).setdefault("auditTrail",[])
            seen_ids = {e.get("eventId") for e in old_trail if e.get("eventId")}
            combined = json.loads(json.dumps(old_trail))
            for event in incoming_trail:
                event_id = event.get("eventId")
                if event_id and event_id in seen_ids:
                    continue
                if not event_id and event in combined:
                    continue
                combined.append(event)
                if event_id:
                    seen_ids.add(event_id)
            data["panel"]["metadata"]["auditTrail"] = combined
            if audit_import:
                append_audit(
                    data,
                    "panel_import_replaced",
                    panel_id,
                    {"changes": panel_change_summary(existing_data, data)},
                )
            db.execute(
                """UPDATE panels SET panel_name=?,category=?,business=?,region_level=?,region_value=?,owner=?,mdf_code=?,data_json=?,updated_at=? WHERE panel_id=?""",
                (core["panelName"],category,business,region_level,region_value,owner,lead,json.dumps(data),ts,panel_id),
            )
        else:
            if audit_import:
                append_audit(
                    data,
                    "panel_imported",
                    panel_id,
                    {"sourceSchemaVersion": payload.get("schemaVersion", 1)},
                )
            created = data["panel"]["metadata"].get("createdAt") or ts
            db.execute(
                """INSERT INTO panels(panel_id,panel_name,category,business,region_level,region_value,owner,mdf_code,data_json,created_at,updated_at)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                (panel_id,core["panelName"],category,business,region_level,region_value,owner,lead,json.dumps(data),created,ts),
            )
        db.commit()
        return panel_id

    def get_mdf_codes(include_inactive=False):
        sql = "SELECT code,description,active FROM mdf_codes"
        params = ()
        if not include_inactive:
            sql += " WHERE active=1"
        sql += " ORDER BY code"
        return [dict(row) for row in get_db().execute(sql, params).fetchall()]


    def generic_supplier_address(bpid):
        digits = "".join(ch for ch in str(bpid) if ch.isdigit()) or "0"
        n = int(digits[-4:]) if digits else 0
        unit = (n % 180) + 1
        estate = ["Supplier Business Park", "Industrial Estate", "Commerce Park", "Technology Park"][n % 4]
        town = ["Stafford", "Birmingham", "Manchester", "Leeds", "Nottingham", "Bristol"][n % 6]
        postcode = ["ST16 1AA", "B1 1AA", "M1 1AA", "LS1 1AA", "NG1 1AA", "BS1 1AA"][n % 6]
        return f"Unit {unit}, {estate}, {town}, UK", postcode

    def import_supplier_rows(rows):
        db = get_db()
        imported = updated = skipped = 0
        ts = now_iso()
        for row in rows:
            bpid = str(row.get("BPID") or row.get("bpid") or "").strip()
            name = str(row.get("Supplier_Name") or row.get("supplier_name") or row.get("Name") or "").strip()
            if not bpid or not name:
                skipped += 1
                continue
            address = str(row.get("Address") or row.get("address") or "").strip()
            post_code = str(row.get("Post_Code") or row.get("PostCode") or row.get("post_code") or "").strip()
            address_source = "source"
            if not address:
                address, generated_post = generic_supplier_address(bpid)
                address_source = "generated"
                if not post_code:
                    post_code = generated_post
            existing = db.execute("SELECT bpid FROM supplier_master WHERE bpid=?", (bpid,)).fetchone()
            if existing:
                db.execute(
                    """UPDATE supplier_master
                       SET supplier_name=?,address=?,post_code=?,address_source=?,active=1,updated_at=?
                       WHERE bpid=?""",
                    (name,address,post_code,address_source,ts,bpid),
                )
                updated += 1
            else:
                db.execute(
                    """INSERT INTO supplier_master
                       (bpid,supplier_name,address,post_code,address_source,active,created_at,updated_at)
                       VALUES(?,?,?,?,?,1,?,?)""",
                    (bpid,name,address,post_code,address_source,ts,ts),
                )
                imported += 1
        db.commit()
        return imported, updated, skipped

    def supplier_master_search(query, include_inactive=False, limit=30):
        q = (query or "").strip()
        sql = """SELECT bpid,supplier_name,address,post_code,address_source,active
                 FROM supplier_master"""
        params = []
        where = []
        if not include_inactive:
            where.append("active=1")
        if q:
            where.append("(bpid LIKE ? OR supplier_name LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like])
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += """ ORDER BY
                    CASE WHEN bpid = ? THEN 0
                         WHEN bpid LIKE ? THEN 1
                         WHEN supplier_name LIKE ? THEN 2
                         ELSE 3 END,
                    supplier_name
                 LIMIT ?"""
        exact = q
        prefix = f"{q}%"
        params.extend([exact, prefix, prefix, int(limit)])
        return [dict(row) for row in get_db().execute(sql, params).fetchall()]


    DEFAULT_DASHBOARD_CONFIG = {
        "baseCurrency": "GBP",
        "spendFieldId": "annual_spend",
        "currencyFieldId": "spend_currency",
        "qualificationFieldId": "qualification_status",
        "qualificationReviewFieldId": "qualification_review_date",
        "classificationFieldId": "classification",
        "currencyRates": {"GBP": 1.0, "EUR": 0.86, "USD": 0.78},
    }

    def get_dashboard_config():
        row = get_db().execute("SELECT value FROM app_settings WHERE key='dashboard_config'").fetchone()
        if row is None:
            return json.loads(json.dumps(DEFAULT_DASHBOARD_CONFIG))
        try:
            loaded = json.loads(row["value"])
        except (json.JSONDecodeError, TypeError):
            return json.loads(json.dumps(DEFAULT_DASHBOARD_CONFIG))
        config = json.loads(json.dumps(DEFAULT_DASHBOARD_CONFIG))
        config.update({k:v for k,v in loaded.items() if k in config})
        rates = loaded.get("currencyRates")
        if isinstance(rates, dict):
            clean_rates = {}
            for code, rate in rates.items():
                try:
                    clean_rates[str(code).upper()] = float(rate)
                except (TypeError, ValueError):
                    continue
            if clean_rates:
                config["currencyRates"] = clean_rates
        config["baseCurrency"] = str(config.get("baseCurrency") or "GBP").upper()
        config["currencyRates"].setdefault(config["baseCurrency"], 1.0)
        return config

    def save_dashboard_config(config):
        get_db().execute(
            """INSERT INTO app_settings(key,value,updated_at) VALUES('dashboard_config',?,?)
               ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=excluded.updated_at""",
            (json.dumps(config), now_iso()),
        )
        get_db().commit()

    def convert_spend(amount, currency, config):
        try:
            amount = float(amount)
        except (TypeError, ValueError):
            return None
        currency = str(currency or config["baseCurrency"]).upper()
        rate = config["currencyRates"].get(currency)
        if rate is None:
            return None
        return amount * float(rate)

    def panel_qualification_status(suppliers, field_id):
        statuses = []
        for supplier in suppliers:
            value = str(supplier.get("customFields",{}).get(field_id) or "").strip()
            if value:
                statuses.append(value)
        if not statuses:
            return "No data"

        def severity(value):
            normalized = value.strip().lower()
            if normalized in {"not qualified", "unqualified", "rejected", "failed"}:
                return 3
            if normalized in {"in review", "under review", "pending", "conditional"}:
                return 2
            if normalized in {"qualified", "approved"}:
                return 1
            return 2

        return max(statuses, key=severity)

    def qualification_review_bucket(value):
        if not value:
            return "missing"
        try:
            review_date = datetime.fromisoformat(str(value)).date()
        except (TypeError, ValueError):
            return "invalid"
        today = datetime.now(timezone.utc).date()
        days = (review_date - today).days
        if days < 0:
            return "overdue"
        if days <= 30:
            return "due_30"
        return "future"

    @app.context_processor
    def inject_globals():
        return dict(categories=CATEGORIES,businesses=BUSINESSES,region_levels=REGION_LEVELS,mdf_codes=get_mdf_codes())

    @app.route("/")
    def portfolio():
        if request.args.get("clear") == "1":
            session.pop("portfolio_filters", None)
            return redirect(url_for("portfolio"))

        saved = session.get("portfolio_filters", {})
        filter_keys = ("q", "category", "business", "sort", "direction", "page_size")
        explicit_filters = any(key in request.args for key in filter_keys)
        if explicit_filters:
            filters = {
                "q": request.args.get("q","").strip(),
                "category": request.args.get("category",""),
                "business": request.args.get("business",""),
                "sort": request.args.get("sort","updated"),
                "direction": request.args.get("direction","desc"),
                "page_size": request.args.get("page_size","20"),
            }
            session["portfolio_filters"] = filters
        else:
            filters = {
                "q": saved.get("q",""),
                "category": saved.get("category",""),
                "business": saved.get("business",""),
                "sort": saved.get("sort","updated"),
                "direction": saved.get("direction","desc"),
                "page_size": saved.get("page_size","20"),
            }

        show_archived = request.args.get("archived","") == "1"
        favourites_only = request.args.get("favourites","") == "1"
        rows = get_db().execute("SELECT * FROM panels").fetchall()
        all_panels = [row_to_panel(r) for r in rows]
        panels = [p for p in all_panels if show_archived or not p.get("archived_at")]
        if favourites_only:
            panels = [p for p in panels if p.get("is_favourite")]

        search = filters["q"].lower()
        category = filters["category"]
        business = filters["business"]
        if search:
            panels = [p for p in panels if search in " ".join([p["panel_id"],p["panel_name"],p["category"],p["business"],p["region_value"],p["owner"],p["mdf_code"]]).lower()]
        if category:
            panels = [p for p in panels if p["category"] == category]
        if business:
            panels = [p for p in panels if p["business"] == business]

        sort_key = filters["sort"] if filters["sort"] in {"panel","mdf","category","business","region","owner","suppliers","updated"} else "updated"
        direction = "asc" if filters["direction"] == "asc" else "desc"
        reverse = direction == "desc"
        def portfolio_sort_value(panel):
            core = panel["data"]["panel"]
            values = {
                "panel": panel["panel_name"].lower(),
                "mdf": panel["mdf_code"].lower(),
                "category": panel["category"].lower(),
                "business": panel["business"].lower(),
                "region": panel["region_value"].lower(),
                "owner": panel["owner"].lower(),
                "suppliers": len(core.get("suppliers",[])),
                "updated": panel["updated_at"],
            }
            return values[sort_key]
        panels.sort(key=portfolio_sort_value, reverse=reverse)

        try:
            page_size = int(filters["page_size"])
        except (TypeError, ValueError):
            page_size = 20
        if page_size not in {10,20,50,100}:
            page_size = 20
        filters["page_size"] = str(page_size)
        try:
            page = max(int(request.args.get("page","1")), 1)
        except ValueError:
            page = 1
        filtered_total = len(panels)
        page_count = max((filtered_total + page_size - 1) // page_size, 1)
        page = min(page, page_count)
        start = (page - 1) * page_size
        panels = panels[start:start + page_size]

        config = get_dashboard_config()
        supplier_count = 0
        supplier_occurrences = {}
        spend_by_category = {}
        unconverted_spend = {}
        qualifications = {}
        classifications = {}
        qualification_reviews = {"overdue":0,"due_30":0,"future":0,"missing":0,"invalid":0}
        for p in all_panels:
            if p.get("archived_at"):
                continue
            suppliers = p["data"]["panel"].get("suppliers",[])
            supplier_count += len(suppliers)
            panel_spend = 0.0
            for supplier in suppliers:
                supplier_name = supplier.get("supplierName") or supplier.get("supplierId") or "Unknown"
                supplier_occurrences[supplier_name] = supplier_occurrences.get(supplier_name,0) + 1
                custom = supplier.get("customFields",{})
                amount = custom.get(config["spendFieldId"])
                currency = custom.get(config["currencyFieldId"]) or config["baseCurrency"]
                converted = convert_spend(amount, currency, config)
                if converted is not None:
                    spend_by_category[p["category"]] = spend_by_category.get(p["category"],0) + converted
                    panel_spend += converted
                elif amount not in (None,""):
                    code = str(currency or config["baseCurrency"]).upper()
                    try:
                        unconverted_spend[code] = unconverted_spend.get(code,0) + float(amount)
                    except (TypeError, ValueError):
                        pass
                q = custom.get(config["qualificationFieldId"])
                c = custom.get(config["classificationFieldId"])
                if q:
                    qualifications[q] = qualifications.get(q,0) + 1
                if c:
                    classifications[c] = classifications.get(c,0) + 1
                bucket = qualification_review_bucket(custom.get(config["qualificationReviewFieldId"]))
                qualification_reviews[bucket] += 1
            p["dashboard_spend"] = panel_spend
            p["panel_qualification"] = panel_qualification_status(
                suppliers,
                config["qualificationFieldId"],
            )
        top_spend = sorted(spend_by_category.items(), key=lambda x:x[1], reverse=True)[:4]
        top_suppliers = sorted(supplier_occurrences.items(), key=lambda x:(-x[1], x[0].lower()))[:5]
        active_total = sum(1 for p in all_panels if not p.get("archived_at"))
        archived_total = len(all_panels) - active_total
        favourite_total = sum(1 for p in all_panels if p.get("is_favourite") and not p.get("archived_at"))
        return render_template(
            "portfolio.html",
            panels=panels,
            total_panels=active_total,
            filtered_total=filtered_total,
            supplier_count=supplier_count,
            top_spend=top_spend,
            top_suppliers=top_suppliers,
            dashboard_config=config,
            unconverted_spend=unconverted_spend,
            qualifications=qualifications,
            qualification_reviews=qualification_reviews,
            classifications=classifications,
            show_archived=show_archived,
            favourites_only=favourites_only,
            archived_total=archived_total,
            favourite_total=favourite_total,
            filters=filters,
            page=page,
            page_count=page_count,
            page_size=page_size,
            sort_key=sort_key,
            direction=direction,
        )

    @app.route("/panels/<panel_id>/favourite", methods=["POST"])
    def panel_favourite(panel_id):
        panel = get_panel_or_404(panel_id)
        new_value = 0 if panel.get("is_favourite") else 1
        get_db().execute("UPDATE panels SET is_favourite=? WHERE id=?", (new_value, panel["id"]))
        get_db().commit()
        return_to = request.form.get("return_to","")
        if not return_to.startswith("/") or return_to.startswith("//"):
            return_to = url_for("portfolio")
        return redirect(return_to)

    @app.route("/panels/import", methods=["GET","POST"])
    def panel_import():
        if request.method == "POST":
            upload = request.files.get("panel_file")
            if upload is None or not upload.filename:
                flash("Choose a panel JSON file to import.","error")
                return render_template("panel_import.html"),400
            try:
                payload = json.loads(upload.stream.read().decode("utf-8-sig"))
                panel_id = persist_imported_panel(
                    payload,
                    replace_existing=request.form.get("replace_existing") == "1",
                    audit_import=True,
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError, TypeError) as exc:
                flash(f"Panel import failed: {exc}","error")
                return render_template("panel_import.html"),400
            flash(f"Panel {panel_id} imported successfully.","success")
            return redirect(url_for("panel_view",panel_id=panel_id))
        return render_template("panel_import.html")

    @app.route("/panels/<panel_id>/export")
    def panel_export(panel_id):
        panel = get_panel_or_404(panel_id)
        body = json.dumps(panel["data"], indent=2, ensure_ascii=False) + "\n"
        response = app.response_class(body, mimetype="application/json")
        response.headers["Content-Disposition"] = f'attachment; filename="{panel_id}.json"'
        return response

    @app.route("/api/field-templates", methods=["GET", "POST"])
    def field_templates():
        db = get_db()
        if request.method == "GET":
            rows = db.execute("SELECT * FROM field_templates ORDER BY field_name COLLATE NOCASE").fetchall()
            return jsonify([{
                "templateId": row["template_id"], "fieldName": row["field_name"],
                "type": row["field_type"], "options": json.loads(row["options_json"]),
                "required": bool(row["required"]),
            } for row in rows])
        body = request.get_json(silent=True)
        if not isinstance(body, dict):
            return jsonify({"error": "Expected field JSON object."}), 400
        try:
            fields = parse_fields(json.dumps([body]))
        except (TypeError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 400
        field = fields[0]
        tid = uuid4().hex
        db.execute("INSERT INTO field_templates(template_id,field_name,field_type,options_json,required,updated_at) VALUES(?,?,?,?,?,?)",
                   (tid, field["fieldName"], field["type"], json.dumps(field["options"]), int(field["required"]), now_iso()))
        db.commit()
        return jsonify({"templateId": tid, "fieldName": field["fieldName"],
                        "type": field["type"], "options": field["options"],
                        "required": field["required"]}), 201

    @app.route("/panels/new", methods=["GET","POST"])
    def panel_new():
        if request.method == "POST":
            return save_panel()
        return render_template("panel_form.html",panel=None)

    @app.route("/panels/<panel_id>/duplicate", methods=["GET", "POST"])
    def panel_duplicate(panel_id):
        source = get_panel_or_404(panel_id)
        if request.method == "POST":
            return save_panel(source=source)
        prefill = dict(source)
        prefill["panel_id"] = ""
        prefill["panel_name"] = "Copy of " + source["panel_name"]
        return render_template("panel_form.html", panel=None, prefill=prefill,
                               duplicate_source=source)

    @app.route("/panels/<panel_id>/edit", methods=["GET","POST"])
    def panel_edit(panel_id):
        panel = get_panel_or_404(panel_id)
        if request.method == "POST":
            return save_panel(panel)
        return render_template("panel_form.html",panel=panel)

    @app.route("/panels/<panel_id>/configuration", methods=["GET","POST"])
    def panel_configuration(panel_id):
        panel = get_panel_or_404(panel_id)
        if request.method == "POST":
            return save_panel_configuration(panel)
        return render_template("panel_configuration.html", panel=panel)

    def save_panel(existing=None, source=None):
        panel_id = request.form.get("panel_id","").strip()
        panel_name = request.form.get("panel_name","").strip()
        category = request.form.get("category","")
        business = request.form.get("business","")
        region_level = request.form.get("region_level","")
        region_value = request.form.get("region_value","").strip()
        owner = request.form.get("owner","").strip()
        mdf_codes = [x for x in request.form.getlist("mdf_codes") if x]
        lead_mdf_code = request.form.get("lead_mdf_code","").strip()
        if not all([panel_id,panel_name,category,business,region_level,owner]) or not mdf_codes or not lead_mdf_code:
            flash("Complete all required panel fields.","error")
            return render_template("panel_form.html",panel=existing),400
        if category not in CATEGORIES or business not in BUSINESSES or region_level not in REGION_LEVELS:
            flash("One or more controlled values are invalid.","error")
            return render_template("panel_form.html",panel=existing),400
        active_mdf = {m["code"] for m in get_mdf_codes()}
        existing_mdf = set(existing["data"]["panel"].get("mdfCodes", [existing.get("mdf_code")]) if existing else [])
        allowed_mdf = active_mdf | existing_mdf | set(source["data"]["panel"].get("mdfCodes", []) if source else [])
        if any(code not in allowed_mdf for code in mdf_codes) or lead_mdf_code not in mdf_codes:
            flash("Select one or more valid MDF codes and choose the lead MDF from those selected.","error")
            return render_template("panel_form.html",panel=existing),400

        db = get_db()
        suppliers = existing["data"]["panel"].get("suppliers",[]) if existing else []
        created_at = existing["created_at"] if existing else now_iso()
        value = region_value or region_level
        existing_metadata = json.loads(json.dumps(existing["data"]["panel"].get("metadata", {}))) if existing else None

        if existing or source:
            field_groups = json.loads(json.dumps((existing or source)["data"]["panel"].get("fieldGroups", [])))
            fields = json.loads(json.dumps((existing or source)["data"]["panel"].get("supplierFields", [])))
        else:
            try:
                field_groups = parse_field_groups(request.form.get("field_groups_json","[]"))
                fields = parse_fields(request.form.get("fields_json","[]"))
                group_ids = {g["groupId"] for g in field_groups}
                unknown_groups = sorted({f["groupId"] for f in fields if f.get("groupId") and f["groupId"] not in group_ids})
                if unknown_groups:
                    raise ValueError("Custom fields reference unknown field groups: " + ", ".join(unknown_groups))
            except ValueError as exc:
                flash(str(exc),"error")
                return render_template("panel_form.html",panel=existing),400

        payload = build_panel_payload(panel_id,panel_name,category,business,region_level,value,owner,mdf_codes,lead_mdf_code,field_groups,fields,suppliers,created_at,existing_metadata)
        if existing and "dashboardWidgets" in existing["data"]["panel"]:
            payload["panel"]["dashboardWidgets"] = json.loads(json.dumps(existing["data"]["panel"]["dashboardWidgets"]))
        if source:
            # A duplicate is a fresh aggregate: no supplier records, history or orphaned values.
            # Carry over optional panel configuration such as future KPI widget definitions.
            source_core = source["data"]["panel"]
            for key in ("dashboardWidgets",):
                if key in source_core:
                    payload["panel"][key] = json.loads(json.dumps(source_core[key]))
            payload["panel"]["suppliers"] = []
        if existing:
            changes = panel_change_summary(existing["data"], payload)
            if changes:
                append_audit(payload, "panel_updated", panel_id, {"changes": changes})
        else:
            append_audit(payload, "panel_duplicated" if source else "panel_created", panel_id, {
                **({"sourcePanelId": source["panel_id"]} if source else {}),
                "panelName": panel_name,
                "category": category,
                "business": business,
                "region": {"level": region_level, "value": value},
                "leadMdfCode": lead_mdf_code,
                "mdfCodes": mdf_codes,
            })
        ts = now_iso()
        try:
            if existing:
                db.execute("""UPDATE panels SET panel_name=?,category=?,business=?,region_level=?,region_value=?,owner=?,mdf_code=?,data_json=?,updated_at=? WHERE id=?""",
                           (panel_name,category,business,region_level,value,owner,lead_mdf_code,json.dumps(payload),ts,existing["id"]))
            else:
                db.execute("""INSERT INTO panels(panel_id,panel_name,category,business,region_level,region_value,owner,mdf_code,data_json,created_at,updated_at)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                           (panel_id,panel_name,category,business,region_level,value,owner,lead_mdf_code,json.dumps(payload),ts,ts))
            db.commit()
        except sqlite3.IntegrityError:
            flash("Panel ID must be unique.","error")
            return render_template("panel_form.html",panel=existing),409
        flash("Panel saved.","success")
        return redirect(url_for("panel_view",panel_id=panel_id))

    def save_panel_configuration(panel):
        data = json.loads(json.dumps(panel["data"]))
        core = data["panel"]
        try:
            field_groups = parse_field_groups(request.form.get("field_groups_json","[]"))
            fields = parse_fields(request.form.get("fields_json","[]"))
            group_ids = {g["groupId"] for g in field_groups}
            widgets = parse_dashboard_widgets(request.form.get("dashboard_widgets_json", json.dumps(core.get("dashboardWidgets", []))), fields)
            unknown_groups = sorted({f["groupId"] for f in fields if f.get("groupId") and f["groupId"] not in group_ids})
            if unknown_groups:
                raise ValueError("Custom fields reference unknown field groups: " + ", ".join(unknown_groups))
        except ValueError as exc:
            flash(str(exc),"error")
            return render_template("panel_configuration.html",panel=panel),400

        suppliers = core.get("suppliers", [])
        old_fields = {f["fieldId"]: f for f in core.get("supplierFields",[])}
        new_ids = {f["fieldId"] for f in fields}
        removed_fields = [f for fid,f in old_fields.items() if fid not in new_ids]
        removed_field_impacts = []
        for field in removed_fields:
            affected = []
            for supplier in suppliers:
                value_at_field = supplier.get("customFields",{}).get(field["fieldId"])
                if value_at_field not in (None,""):
                    affected.append({
                        "supplierId": supplier.get("supplierId"),
                        "supplierName": supplier.get("supplierName"),
                        "value": value_at_field,
                    })
            if affected:
                removed_field_impacts.append({
                    "field": field,
                    "affectedCount": len(affected),
                    "examples": affected[:5],
                })

        if removed_field_impacts and request.form.get("confirm_field_removal") != "1":
            form_data = {key: request.form.getlist(key) for key in request.form.keys()}
            return render_template(
                "field_removal_preview.html",
                panel=panel,
                impacts=removed_field_impacts,
                form_data=form_data,
                confirm_endpoint="panel_configuration",
            ),409

        metadata = core.setdefault("metadata", {})
        orphaned = metadata.setdefault("orphanedSupplierFields", {})
        for field in removed_fields:
            affected_count = sum(
                1 for supplier in suppliers
                if supplier.get("customFields",{}).get(field["fieldId"]) not in (None,"")
            )
            orphaned[field["fieldId"]] = {
                "field": field,
                "removedAt": now_iso(),
                "affectedSuppliers": affected_count,
            }
        for field in fields:
            orphaned.pop(field["fieldId"], None)

        before = json.loads(json.dumps(panel["data"]))
        core["fieldGroups"] = field_groups
        core["supplierFields"] = fields
        core["dashboardWidgets"] = widgets
        changes = panel_change_summary(before, data)
        if changes:
            append_audit(data, "panel_configuration_updated", panel["panel_id"], {"changes": changes})
        if removed_fields:
            append_audit(
                data,
                "panel_fields_removed",
                panel["panel_id"],
                {"fields":[{"fieldId":f["fieldId"],"fieldName":f["fieldName"]} for f in removed_fields]},
            )
        save_panel_data(panel, data)
        flash("Panel configuration saved.","success")
        return redirect(url_for("panel_configuration",panel_id=panel["panel_id"]))

    def find_supplier(panel, supplier_id):
        for supplier in panel["data"]["panel"].get("suppliers", []):
            if supplier.get("supplierId") == supplier_id:
                return supplier
        return None

    def append_audit(data, action, entity_id, details=None):
        data["schemaVersion"] = max(int(data.get("schemaVersion", 1)), 5)
        metadata = data["panel"].setdefault("metadata", {})
        metadata["version"] = max(int(metadata.get("version", 1)), 5)
        metadata["updatedAt"] = now_iso()
        trail = metadata.setdefault("auditTrail", [])
        trail.append({
            "eventId": str(uuid4()),
            "timestamp": now_iso(),
            "action": action,
            "entityId": entity_id,
            "supplierId": entity_id,
            "actor": session.get("audit_actor", "local-user"),
            "details": details or {},
        })

    def panel_change_summary(before, after):
        before_core = before.get("panel", {}) if before else {}
        after_core = after.get("panel", {}) if after else {}
        changes = {}
        scalar_fields = {
            "panelName": "Panel Name",
            "category": "Category",
            "business": "Business",
            "region": "Region",
            "panelOwner": "Panel Owner",
            "leadMdfCode": "Lead MDF",
            "mdfCodes": "MDF Codes",
        }
        for key, label in scalar_fields.items():
            if before_core.get(key) != after_core.get(key):
                changes[key] = {
                    "label": label,
                    "before": before_core.get(key),
                    "after": after_core.get(key),
                }
        if before_core.get("dashboardWidgets", []) != after_core.get("dashboardWidgets", []):
            changes["dashboardWidgets"] = {"label": "Dashboard widgets",
                                            "before": before_core.get("dashboardWidgets", []),
                                            "after": after_core.get("dashboardWidgets", [])}
        if before_core.get("fieldGroups", []) != after_core.get("fieldGroups", []):
            changes["fieldGroups"] = {
                "label": "Field groups",
                "before": before_core.get("fieldGroups", []),
                "after": after_core.get("fieldGroups", []),
            }
        before_fields = {f.get("fieldId"): f for f in before_core.get("supplierFields", [])}
        after_fields = {f.get("fieldId"): f for f in after_core.get("supplierFields", [])}
        added = [after_fields[k] for k in after_fields.keys() - before_fields.keys()]
        removed = [before_fields[k] for k in before_fields.keys() - after_fields.keys()]
        modified = []
        for field_id in before_fields.keys() & after_fields.keys():
            if before_fields[field_id] != after_fields[field_id]:
                modified.append({
                    "fieldId": field_id,
                    "before": before_fields[field_id],
                    "after": after_fields[field_id],
                })
        if added or removed or modified:
            changes["supplierFields"] = {
                "label": "Supplier field schema",
                "added": added,
                "removed": removed,
                "modified": modified,
            }
        return changes

    def save_panel_data(panel, data):
        get_db().execute(
            "UPDATE panels SET data_json=?,updated_at=? WHERE id=?",
            (json.dumps(data), now_iso(), panel["id"]),
        )
        get_db().commit()

    @app.route("/panels/<panel_id>")
    def panel_view(panel_id):
        panel = get_panel_or_404(panel_id)
        supplier_widgets, supplier_widget_rows = calculate_supplier_widgets(panel["data"]["panel"])
        return render_template("panel_view.html", panel=panel,
                               dashboard_widgets=calculate_dashboard_widgets(panel["data"]["panel"]),
                               supplier_widgets=supplier_widgets, supplier_widget_rows=supplier_widget_rows)

    @app.route("/panels/<panel_id>/fields/orphans")
    def orphan_fields(panel_id):
        panel = get_panel_or_404(panel_id)
        orphans = panel["data"]["panel"].get("metadata",{}).get("orphanedSupplierFields",{})
        rows = []
        for field_id, info in orphans.items():
            values = []
            for supplier in panel["data"]["panel"].get("suppliers",[]):
                value = supplier.get("customFields",{}).get(field_id)
                if value not in (None,""):
                    values.append({
                        "supplierId": supplier.get("supplierId"),
                        "supplierName": supplier.get("supplierName"),
                        "value": value,
                    })
            rows.append({"fieldId":field_id,"info":info,"values":values})
        rows.sort(key=lambda x:(x["info"].get("field",{}).get("fieldName") or x["fieldId"]).lower())
        return render_template("orphan_fields.html",panel=panel,orphans=rows)

    @app.route("/panels/<panel_id>/fields/orphans/<field_id>/restore", methods=["POST"])
    def orphan_field_restore(panel_id, field_id):
        panel = get_panel_or_404(panel_id)
        data = panel["data"]
        metadata = data["panel"].setdefault("metadata",{})
        orphans = metadata.setdefault("orphanedSupplierFields",{})
        info = orphans.get(field_id)
        if info is None:
            from flask import abort
            abort(404)
        fields = data["panel"].setdefault("supplierFields",[])
        if not any(f.get("fieldId") == field_id for f in fields):
            restored = json.loads(json.dumps(info.get("field",{})))
            restored["order"] = len(fields) + 1
            fields.append(restored)
        orphans.pop(field_id,None)
        append_audit(data,"orphan_field_restored",panel_id,{"fieldId":field_id})
        save_panel_data(panel,data)
        flash(f"Field {field_id} restored with its preserved supplier values.","success")
        return redirect(url_for("panel_view",panel_id=panel_id))

    @app.route("/panels/<panel_id>/fields/orphans/<field_id>/purge", methods=["POST"])
    def orphan_field_purge(panel_id, field_id):
        panel = get_panel_or_404(panel_id)
        data = panel["data"]
        metadata = data["panel"].setdefault("metadata",{})
        orphans = metadata.setdefault("orphanedSupplierFields",{})
        info = orphans.get(field_id)
        if info is None:
            from flask import abort
            abort(404)
        confirmation = request.form.get("confirm_field_id","").strip()
        if confirmation != field_id:
            flash("Orphan data was not purged: confirmation did not match the field ID.","error")
            return redirect(url_for("orphan_fields",panel_id=panel_id))
        snapshots = []
        for supplier in data["panel"].get("suppliers",[]):
            custom = supplier.get("customFields",{})
            if field_id in custom:
                snapshots.append({
                    "supplierId": supplier.get("supplierId"),
                    "value": custom.get(field_id),
                })
                custom.pop(field_id,None)
        snapshot_info = json.loads(json.dumps(info))
        orphans.pop(field_id,None)
        append_audit(
            data,
            "orphan_field_purged",
            panel_id,
            {"fieldId":field_id,"field":snapshot_info,"values":snapshots},
        )
        save_panel_data(panel,data)
        flash(f"Orphan field data for {field_id} purged. A recovery snapshot remains in the audit trail.","success")
        return redirect(url_for("orphan_fields",panel_id=panel_id))

    @app.route("/panels/<panel_id>/suppliers/new", methods=["GET","POST"])
    def supplier_new(panel_id):
        panel = get_panel_or_404(panel_id)
        if request.method == "POST":
            data = panel["data"]
            suppliers = data["panel"].setdefault("suppliers",[])
            supplier_id = request.form.get("supplier_id","").strip()
            if not supplier_id or any(s["supplierId"] == supplier_id for s in suppliers):
                flash("Supplier ID is required and must be unique within the panel.","error")
                return render_template("supplier_form.html",panel=panel,supplier=None),400
            master = get_db().execute(
                "SELECT * FROM supplier_master WHERE bpid=? AND active=1",
                (supplier_id,),
            ).fetchone()
            supplier_name = request.form.get("supplier_name","").strip()
            address = request.form.get("address","").strip()
            post_code = request.form.get("post_code","").strip()
            if master is not None:
                supplier_name = master["supplier_name"]
                address = master["address"]
                post_code = master["post_code"]
            if not supplier_name:
                flash("Supplier Name is required. Select a master supplier or enter a manual supplier.","error")
                return render_template("supplier_form.html",panel=panel,supplier=None),400
            custom = {}
            for field in data["panel"].get("supplierFields",[]):
                value = request.form.get(f"custom_{field['fieldId']}","")
                if field["type"] == "multiselect_blocks":
                    try:
                        value = parse_multiselect_value(field, request.form.getlist(f"custom_{field['fieldId']}"))
                    except ValueError as exc:
                        flash(str(exc), "error")
                        return render_template("supplier_form.html", panel=panel, supplier=locals().get("previous")), 400
                if field["type"] == "boolean":
                    value = True if value == "true" else False if value == "false" else None
                if field["type"] == "stars" and value != "":
                    try:
                        rating = float(value)
                        if not (0 <= rating <= 5 and rating * 2 == int(rating * 2)):
                            raise ValueError()
                        value = rating
                    except (ValueError, OverflowError):
                        flash(f"{field['fieldName']} must be 0–5 in steps of 0.5.", "error")
                        return render_template("supplier_bulk_edit.html" if "supplier_id" in locals() and "fields" in locals() else "supplier_form.html", panel=panel, supplier=locals().get("previous")), 400
                if field["type"] == "number" and value != "":
                    try: value = float(value)
                    except ValueError:
                        flash(f"{field['fieldName']} must be numeric.","error")
                        return render_template("supplier_form.html",panel=panel),400
                custom[field["fieldId"]] = value
            suppliers.append({"supplierId":supplier_id,"supplierName":supplier_name,"address":address,"postCode":post_code,"masterLinked":master is not None,"customFields":custom})
            append_audit(data, "supplier_created", supplier_id, {"supplierName": supplier_name, "masterLinked": master is not None})
            save_panel_data(panel, data)
            flash("Supplier added.","success")
            return redirect(url_for("panel_view",panel_id=panel_id))
        return render_template("supplier_form.html",panel=panel,supplier=None)

    @app.route("/panels/<panel_id>/suppliers/<supplier_id>/edit", methods=["GET","POST"])
    def supplier_edit(panel_id, supplier_id):
        panel = get_panel_or_404(panel_id)
        supplier = find_supplier(panel, supplier_id)
        if supplier is None:
            from flask import abort
            abort(404)
        if request.method == "POST":
            data = panel["data"]
            previous = json.loads(json.dumps(supplier))
            new_name = request.form.get("supplier_name","").strip()
            if not new_name:
                flash("Supplier Name is required.","error")
                return render_template("supplier_form.html",panel=panel,supplier=supplier),400
            supplier["supplierName"] = new_name
            supplier["address"] = request.form.get("address","").strip()
            supplier["postCode"] = request.form.get("post_code","").strip()
            custom = supplier.setdefault("customFields", {})
            for field in data["panel"].get("supplierFields",[]):
                value = request.form.get(f"custom_{field['fieldId']}","")
                if field["type"] == "boolean":
                    value = True if value == "true" else False if value == "false" else None
                if field["type"] == "stars" and value != "":
                    try:
                        rating = float(value)
                        if not (0 <= rating <= 5 and rating * 2 == int(rating * 2)):
                            raise ValueError()
                        value = rating
                    except (ValueError, OverflowError):
                        flash(f"{field['fieldName']} must be 0–5 in steps of 0.5.", "error")
                        return render_template("supplier_bulk_edit.html" if "supplier_id" in locals() and "fields" in locals() else "supplier_form.html", panel=panel, supplier=locals().get("previous")), 400
                if field["type"] == "number" and value != "":
                    try:
                        value = float(value)
                    except ValueError:
                        flash(f"{field['fieldName']} must be numeric.","error")
                        return render_template("supplier_form.html",panel=panel,supplier=previous),400
                custom[field["fieldId"]] = value
            append_audit(data, "supplier_updated", supplier_id, {"before": previous, "after": json.loads(json.dumps(supplier))})
            save_panel_data(panel, data)
            flash("Supplier updated.","success")
            return redirect(url_for("panel_view",panel_id=panel_id))
        return render_template("supplier_form.html",panel=panel,supplier=supplier)

    @app.route("/panels/<panel_id>/suppliers/bulk-edit", methods=["GET","POST"])
    def supplier_bulk_edit(panel_id):
        panel = get_panel_or_404(panel_id)
        data = panel["data"]
        suppliers = data["panel"].get("suppliers", [])
        fields = data["panel"].get("supplierFields", [])
        if request.method == "POST":
            changed = []
            for supplier in suppliers:
                supplier_id = supplier.get("supplierId")
                custom = supplier.setdefault("customFields", {})
                before = json.loads(json.dumps(custom))
                for field in fields:
                    key = f"{supplier_id}__{field['fieldId']}"
                    value = request.form.get(key, "")
                    if field["type"] == "multiselect_blocks":
                        try:
                            value = parse_multiselect_value(field, request.form.getlist(key))
                        except ValueError as exc:
                            flash(str(exc), "error")
                            return render_template("supplier_bulk_edit.html", panel=panel), 400
                    if field["type"] == "boolean":
                        value = True if value == "true" else False if value == "false" else None
                    if field["type"] == "stars" and value != "":
                        try:
                            rating = float(value)
                            if not (0 <= rating <= 5 and rating * 2 == int(rating * 2)):
                                raise ValueError()
                            value = rating
                        except (ValueError, OverflowError):
                            flash(f"{supplier_id}: {field['fieldName']} must be 0–5 in steps of 0.5.", "error")
                            return render_template("supplier_bulk_edit.html", panel=panel), 400
                    if field["type"] == "number" and value != "":
                        try:
                            value = float(value)
                        except ValueError:
                            flash(f"{supplier_id}: {field['fieldName']} must be numeric.", "error")
                            return render_template("supplier_bulk_edit.html", panel=panel), 400
                    custom[field["fieldId"]] = value
                if custom != before:
                    changed.append({
                        "supplierId": supplier_id,
                        "before": before,
                        "after": json.loads(json.dumps(custom)),
                    })
            if changed:
                append_audit(data, "supplier_bulk_custom_fields_updated", panel_id, {"changes": changed})
                save_panel_data(panel, data)
                flash(f"Updated custom fields for {len(changed)} supplier(s).","success")
            else:
                flash("No supplier custom-field changes were made.","success")
            return redirect(url_for("panel_view", panel_id=panel_id))
        return render_template("supplier_bulk_edit.html", panel=panel)

    @app.route("/panels/<panel_id>/suppliers/<supplier_id>/delete", methods=["POST"])
    def supplier_delete(panel_id, supplier_id):
        panel = get_panel_or_404(panel_id)
        data = panel["data"]
        supplier = find_supplier(panel, supplier_id)
        if supplier is None:
            from flask import abort
            abort(404)
        confirmation = request.form.get("confirm_supplier_id","").strip()
        if confirmation != supplier_id:
            flash("Supplier was not deleted: confirmation did not match the Supplier ID.","error")
            return redirect(url_for("panel_view",panel_id=panel_id))
        snapshot = json.loads(json.dumps(supplier))
        data["panel"]["suppliers"] = [s for s in data["panel"].get("suppliers",[]) if s.get("supplierId") != supplier_id]
        append_audit(data, "supplier_deleted", supplier_id, {"snapshot": snapshot})
        save_panel_data(panel, data)
        flash(f"Supplier {supplier_id} deleted. A recovery snapshot was retained in the panel audit trail.","success")
        return redirect(url_for("panel_view",panel_id=panel_id))

    @app.route("/panels/<panel_id>/archive", methods=["POST"])
    def panel_archive(panel_id):
        panel = get_panel_or_404(panel_id)
        confirmation = request.form.get("confirm_panel_id","").strip()
        if confirmation != panel_id:
            flash("Panel was not archived: confirmation did not match the Panel ID.","error")
            return redirect(url_for("panel_view",panel_id=panel_id))
        if panel.get("archived_at"):
            flash("Panel is already archived.","error")
            return redirect(url_for("panel_view",panel_id=panel_id))
        data = panel["data"]
        archived_at = now_iso()
        metadata = data["panel"].setdefault("metadata",{})
        metadata["status"] = "archived"
        metadata["archivedAt"] = archived_at
        append_audit(data, "panel_archived", panel_id, {"archivedAt": archived_at})
        get_db().execute("UPDATE panels SET data_json=?,updated_at=?,archived_at=? WHERE id=?",(json.dumps(data),now_iso(),archived_at,panel["id"]))
        get_db().commit()
        flash(f"Panel {panel_id} archived. It remains recoverable.","success")
        return redirect(url_for("portfolio"))

    @app.route("/panels/<panel_id>/restore", methods=["POST"])
    def panel_restore(panel_id):
        panel = get_panel_or_404(panel_id)
        if not panel.get("archived_at"):
            flash("Panel is already active.","error")
            return redirect(url_for("panel_view",panel_id=panel_id))
        data = panel["data"]
        metadata = data["panel"].setdefault("metadata",{})
        metadata["status"] = "active"
        metadata["archivedAt"] = None
        append_audit(data, "panel_restored", panel_id)
        get_db().execute("UPDATE panels SET data_json=?,updated_at=?,archived_at=NULL WHERE id=?",(json.dumps(data),now_iso(),panel["id"]))
        get_db().commit()
        flash(f"Panel {panel_id} restored.","success")
        return redirect(url_for("panel_view",panel_id=panel_id))

    @app.route("/panels/<panel_id>/data", methods=["GET","POST"])
    def panel_data(panel_id):
        panel = get_panel_or_404(panel_id)
        if request.method == "POST":
            raw = request.form.get("raw_json","")
            try:
                payload = migrate_panel_payload(json.loads(raw))
                core = payload["panel"]
                if core["panelId"] != panel_id:
                    raise ValueError("Panel ID cannot be changed from the raw-data editor.")
                previous_trail = panel["data"]["panel"].get("metadata",{}).get("auditTrail",[])
                incoming_meta = core.setdefault("metadata",{})
                incoming_meta["auditTrail"] = json.loads(json.dumps(previous_trail))
                changes = panel_change_summary(panel["data"], payload)
                append_audit(
                    payload,
                    "raw_json_updated",
                    panel_id,
                    {"changes": changes, "supplierCount": len(core.get("suppliers",[]))},
                )
                persist_imported_panel(payload, replace_existing=True)
            except (json.JSONDecodeError,KeyError,TypeError,ValueError) as exc:
                flash(f"JSON not saved: {exc}","error")
                return render_template("data_settings.html",panel=panel,raw_json=raw),400
            flash("Panel JSON updated.","success")
            return redirect(url_for("panel_data",panel_id=panel_id))
        return render_template("data_settings.html",panel=panel,raw_json=json.dumps(panel["data"],indent=2))

    @app.route("/panels/<panel_id>/audit")
    def panel_audit(panel_id):
        panel = get_panel_or_404(panel_id)
        trail = list(panel["data"]["panel"].get("metadata",{}).get("auditTrail",[]))
        trail.reverse()
        action_filter = request.args.get("action","").strip()
        query = request.args.get("q","").strip().lower()
        if action_filter:
            trail = [event for event in trail if event.get("action") == action_filter]
        if query:
            trail = [
                event for event in trail
                if query in json.dumps(event, ensure_ascii=False).lower()
            ]
        actions = sorted({
            event.get("action")
            for event in panel["data"]["panel"].get("metadata",{}).get("auditTrail",[])
            if event.get("action")
        })
        return render_template(
            "audit_log.html",
            panel=panel,
            events=trail,
            actions=actions,
            action_filter=action_filter,
            query=request.args.get("q","").strip(),
        )

    @app.route("/settings")
    def settings_home():
        supplier_total = get_db().execute("SELECT COUNT(*) FROM supplier_master WHERE active=1").fetchone()[0]
        mdf_total = get_db().execute("SELECT COUNT(*) FROM mdf_codes WHERE active=1").fetchone()[0]
        return render_template(
            "settings_home.html",
            supplier_total=supplier_total,
            mdf_total=mdf_total,
        )

    @app.route("/settings/dashboard", methods=["GET","POST"])
    def dashboard_settings():
        config = get_dashboard_config()
        known_fields = {}
        for row in get_db().execute("SELECT data_json FROM panels").fetchall():
            try:
                for field in json.loads(row["data_json"]).get("panel",{}).get("supplierFields",[]):
                    fid = str(field.get("fieldId") or "").strip()
                    if fid:
                        known_fields[fid] = {
                            "fieldId": fid,
                            "fieldName": field.get("fieldName") or fid,
                            "type": field.get("type") or "text",
                        }
            except (json.JSONDecodeError, TypeError):
                pass
        known_fields = sorted(known_fields.values(), key=lambda x:(x["fieldName"].lower(), x["fieldId"].lower()))
        if request.method == "POST":
            base_currency = request.form.get("base_currency","GBP").strip().upper() or "GBP"
            spend_field_id = request.form.get("spend_field_id","annual_spend").strip() or "annual_spend"
            currency_field_id = request.form.get("currency_field_id","spend_currency").strip() or "spend_currency"
            qualification_field_id = request.form.get("qualification_field_id","qualification_status").strip() or "qualification_status"
            qualification_review_field_id = request.form.get("qualification_review_field_id","qualification_review_date").strip() or "qualification_review_date"
            classification_field_id = request.form.get("classification_field_id","classification").strip() or "classification"
            raw_rates = request.form.get("currency_rates","").strip()
            rates = {}
            try:
                for raw_line in raw_rates.splitlines():
                    line = raw_line.strip()
                    if not line:
                        continue
                    code, value = [part.strip() for part in line.split("=",1)]
                    rates[code.upper()] = float(value)
                rates.setdefault(base_currency, 1.0)
            except (ValueError, TypeError):
                flash("Currency rates must use one CODE=rate entry per line, for example EUR=0.86.","error")
                return render_template("dashboard_settings.html",config=config,known_fields=known_fields),400
            config = {
                "baseCurrency": base_currency,
                "spendFieldId": spend_field_id,
                "currencyFieldId": currency_field_id,
                "qualificationFieldId": qualification_field_id,
                "qualificationReviewFieldId": qualification_review_field_id,
                "classificationFieldId": classification_field_id,
                "currencyRates": rates,
            }
            save_dashboard_config(config)
            flash("Dashboard calculation settings updated.","success")
            return redirect(url_for("dashboard_settings"))
        return render_template("dashboard_settings.html",config=config,known_fields=known_fields)

    @app.route("/settings/suppliers", methods=["GET","POST"])
    def supplier_master_settings():
        if request.method == "POST":
            upload = request.files.get("supplier_file")
            if upload is None or not upload.filename:
                flash("Choose a supplier CSV file to import.","error")
                return redirect(url_for("supplier_master_settings"))
            try:
                text = upload.stream.read().decode("utf-8-sig")
                reader = csv.DictReader(io.StringIO(text))
                if not reader.fieldnames or "BPID" not in reader.fieldnames or "Supplier_Name" not in reader.fieldnames:
                    raise ValueError("CSV must contain BPID and Supplier_Name columns.")
                imported, updated, skipped = import_supplier_rows(reader)
                flash(f"Supplier master imported: {imported} new, {updated} updated, {skipped} skipped.","success")
            except (UnicodeDecodeError, csv.Error, ValueError) as exc:
                flash(f"Supplier import failed: {exc}","error")
            return redirect(url_for("supplier_master_settings"))
        q = request.args.get("q","").strip()
        show_removed = request.args.get("removed") == "1"
        suppliers = supplier_master_search(q, include_inactive=show_removed, limit=200)
        total = get_db().execute("SELECT COUNT(*) FROM supplier_master WHERE active=1").fetchone()[0]
        removed = get_db().execute("SELECT COUNT(*) FROM supplier_master WHERE active=0").fetchone()[0]
        return render_template("supplier_master.html",suppliers=suppliers,q=q,show_removed=show_removed,total=total,removed=removed)

    @app.route("/settings/suppliers/<bpid>/remove", methods=["POST"])
    def supplier_master_remove(bpid):
        row = get_db().execute("SELECT * FROM supplier_master WHERE bpid=?", (bpid,)).fetchone()
        if row is None:
            from flask import abort
            abort(404)
        get_db().execute("UPDATE supplier_master SET active=0,updated_at=? WHERE bpid=?", (now_iso(),bpid))
        get_db().commit()
        flash(f"Supplier {bpid} removed from active master selection.","success")
        return redirect(url_for("supplier_master_settings"))

    @app.route("/settings/suppliers/<bpid>/restore", methods=["POST"])
    def supplier_master_restore(bpid):
        row = get_db().execute("SELECT * FROM supplier_master WHERE bpid=?", (bpid,)).fetchone()
        if row is None:
            from flask import abort
            abort(404)
        get_db().execute("UPDATE supplier_master SET active=1,updated_at=? WHERE bpid=?", (now_iso(),bpid))
        get_db().commit()
        flash(f"Supplier {bpid} restored to the active master list.","success")
        return redirect(url_for("supplier_master_settings", removed=1))

    @app.route("/api/supplier-master/search")
    def api_supplier_master_search():
        q = request.args.get("q","").strip()
        if len(q) < 2:
            return jsonify([])
        return jsonify(supplier_master_search(q, include_inactive=False, limit=20))

    @app.route("/settings/mdf", methods=["GET","POST"])
    def mdf_settings():
        if request.method == "POST":
            code = request.form.get("code","").strip().upper()
            description = request.form.get("description","").strip()
            if not code or not description:
                flash("MDF Code and description are required.","error")
                return redirect(url_for("mdf_settings"))
            try:
                get_db().execute(
                    "INSERT INTO mdf_codes(code,description,active,created_at,updated_at) VALUES(?,?,?,?,?)",
                    (code, description, 1, now_iso(), now_iso()),
                )
                get_db().commit()
                flash(f"MDF code {code} added.","success")
            except sqlite3.IntegrityError:
                flash(f"MDF code {code} already exists.","error")
            return redirect(url_for("mdf_settings"))
        return render_template("mdf_settings.html", mdf_codes=get_mdf_codes(include_inactive=True))

    @app.route("/settings/mdf/<code>/update", methods=["POST"])
    def mdf_update(code):
        row = get_db().execute("SELECT * FROM mdf_codes WHERE code=?", (code,)).fetchone()
        if row is None:
            from flask import abort
            abort(404)
        description = request.form.get("description","").strip()
        if not description:
            flash("Description is required.","error")
            return redirect(url_for("mdf_settings"))
        get_db().execute("UPDATE mdf_codes SET description=?,updated_at=? WHERE code=?", (description, now_iso(), code))
        get_db().commit()
        flash(f"MDF code {code} updated.","success")
        return redirect(url_for("mdf_settings"))

    @app.route("/settings/mdf/<code>/toggle", methods=["POST"])
    def mdf_toggle(code):
        row = get_db().execute("SELECT * FROM mdf_codes WHERE code=?", (code,)).fetchone()
        if row is None:
            from flask import abort
            abort(404)
        new_active = 0 if row["active"] else 1
        if new_active == 0:
            in_use = 0
            rows = get_db().execute("SELECT data_json FROM panels WHERE archived_at IS NULL").fetchall()
            for panel_row in rows:
                try:
                    core = json.loads(panel_row["data_json"]).get("panel", {})
                    selected = core.get("mdfCodes") or [core.get("mdfCode")]
                    if code in selected:
                        in_use += 1
                except (json.JSONDecodeError, TypeError):
                    pass
            if in_use:
                flash(f"MDF code {code} is used by {in_use} active panel(s) and cannot be deactivated.","error")
                return redirect(url_for("mdf_settings"))
        get_db().execute("UPDATE mdf_codes SET active=?,updated_at=? WHERE code=?", (new_active, now_iso(), code))
        get_db().commit()
        flash(f"MDF code {code} {'activated' if new_active else 'deactivated'}.","success")
        return redirect(url_for("mdf_settings"))

    @app.route("/api/panels")
    def api_panels():
        rows = get_db().execute("SELECT data_json FROM panels ORDER BY panel_name").fetchall()
        return jsonify([json.loads(r["data_json"]) for r in rows])

    @app.route("/api/panels/<panel_id>")
    def api_panel(panel_id):
        return jsonify(get_panel_or_404(panel_id)["data"])

    with app.app_context():
        init_db()
    return app

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.environ.get("PORT","5000")),debug=True)
