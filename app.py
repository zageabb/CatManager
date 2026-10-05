import json
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import Flask, flash, g, jsonify, redirect, render_template, request, url_for

CATEGORIES = ["Transformers", "Switchgear", "Current Transformers", "Civil Engineering"]
BUSINESSES = ["GI", "GA", "GPQSS", "HVDC"]
REGION_LEVELS = ["Global", "Region", "HUB", "Country"]
FIELD_TYPES = ["number", "text", "dropdown", "date"]
MDF_CODES = [
    {"code": "3GF", "description": "Grid equipment"},
    {"code": "MDF-TR-001", "description": "Power Transformers"},
    {"code": "MDF-SG-001", "description": "High Voltage Switchgear"},
    {"code": "MDF-CT-001", "description": "Current Transformers"},
    {"code": "MDF-CE-001", "description": "Civil Engineering"},
]

def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

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
        """)
        columns = {row[1] for row in db.execute("PRAGMA table_info(panels)").fetchall()}
        if "archived_at" not in columns:
            db.execute("ALTER TABLE panels ADD COLUMN archived_at TEXT")
        db.commit()
        if app.config.get("SEED_DEMO") and db.execute("SELECT COUNT(*) FROM panels").fetchone()[0] == 0:
            seed_demo(db)

    def build_panel_payload(panel_id, panel_name, category, business, region_level, region_value, owner, mdf_code, fields, suppliers, created_at=None):
        return {
            "schemaVersion": 2,
            "panel": {
                "panelId": panel_id,
                "panelName": panel_name,
                "category": category,
                "business": business,
                "region": {"level": region_level, "value": region_value},
                "panelOwner": {"name": owner},
                "mdfCode": mdf_code,
                "supplierFields": fields,
                "suppliers": suppliers,
                "metadata": {"createdAt": created_at or now_iso(), "updatedAt": now_iso(), "version": 2, "auditTrail": []},
            },
        }

    def seed_demo(db):
        examples = [
            ("CMP0261", "Global Transformers", "Transformers", "GI", "Global", "Global", "John Smith", "3GF", 100),
            ("CMP0825", "Europe Switchgear", "Switchgear", "GPQSS", "Region", "Europe", "Alice Brown", "3GF", 40),
            ("CMP0482", "APAC Disconnectors", "Switchgear", "GI", "Region", "APAC", "David Lee", "3GF", 1),
            ("CMP0430", "Global Transformer Services", "Transformers", "GPQSS", "Global", "Global", "Emily Wilson", "3GF", 8),
            ("CMP0751", "Europe Transformers", "Transformers", "GI", "Region", "Europe", "Michael Garcia", "3GF", 15),
            ("CMP0639", "APAC Transformers", "Transformers", "GPQSS", "Region", "APAC", "Sophia Rodriguez", "3GF", 100),
        ]
        for idx, row in enumerate(examples):
            panel_id, name, cat, business, level, value, owner, mdf, spend = row
            fields = [
                {"fieldId":"classification","fieldName":"Classification","type":"dropdown","options":["Standard","Preferred","Critical"],"required":False,"order":1},
                {"fieldId":"qualification_status","fieldName":"Qualification Status","type":"dropdown","options":["In review","Qualified","Not qualified"],"required":False,"order":2},
                {"fieldId":"annual_spend","fieldName":"Annual Spend","type":"number","options":[],"required":False,"order":3},
            ]
            suppliers = []
            for s in range(3 if idx < 3 else 2):
                suppliers.append({
                    "supplierId": f"SUP-{idx+1:02d}{s+1:03d}",
                    "supplierName": ["ABB Systems","Schneider Electric","Hitachi Energy"][s % 3],
                    "address": f"{10+s} Industrial Park",
                    "postCode": "ST16 1AA",
                    "customFields": {
                        "classification": ["Standard","Preferred","Critical"][(idx+s) % 3],
                        "qualification_status": ["Qualified","In review","Not qualified"][(idx+s) % 3],
                        "annual_spend": spend * 1000000 / (s+1),
                    },
                })
            payload = build_panel_payload(panel_id,name,cat,business,level,value,owner,mdf,fields,suppliers)
            ts = now_iso()
            db.execute("""INSERT INTO panels(panel_id,panel_name,category,business,region_level,region_value,owner,mdf_code,data_json,created_at,updated_at)
                          VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                       (panel_id,name,cat,business,level,value,owner,mdf,json.dumps(payload),ts,ts))
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
            options = field.get("options",[]) if ftype == "dropdown" else []
            clean.append({"fieldId":fid,"fieldName":name,"type":ftype,"options":[str(x).strip() for x in options if str(x).strip()],"required":bool(field.get("required",False)),"order":index+1})
        return clean

    @app.context_processor
    def inject_globals():
        return dict(categories=CATEGORIES,businesses=BUSINESSES,region_levels=REGION_LEVELS,mdf_codes=MDF_CODES)

    @app.route("/")
    def portfolio():
        show_archived = request.args.get("archived","") == "1"
        rows = get_db().execute("SELECT * FROM panels ORDER BY updated_at DESC").fetchall()
        all_panels = [row_to_panel(r) for r in rows]
        panels = [p for p in all_panels if show_archived or not p.get("archived_at")]
        search = request.args.get("q","").strip().lower()
        category = request.args.get("category","")
        business = request.args.get("business","")
        if search:
            panels = [p for p in panels if search in " ".join([p["panel_id"],p["panel_name"],p["category"],p["business"],p["region_value"],p["owner"]]).lower()]
        if category:
            panels = [p for p in panels if p["category"] == category]
        if business:
            panels = [p for p in panels if p["business"] == business]

        supplier_count = 0
        spend_by_category = {}
        qualifications = {"In review":0,"Qualified":0,"Not qualified":0}
        classifications = {"Standard":0,"Preferred":0,"Critical":0}
        for p in all_panels:
            suppliers = p["data"]["panel"].get("suppliers",[])
            supplier_count += len(suppliers)
            for supplier in suppliers:
                custom = supplier.get("customFields",{})
                spend_by_category[p["category"]] = spend_by_category.get(p["category"],0) + float(custom.get("annual_spend") or 0)
                q, c = custom.get("qualification_status"), custom.get("classification")
                if q in qualifications: qualifications[q] += 1
                if c in classifications: classifications[c] += 1
        top_spend = sorted(spend_by_category.items(), key=lambda x:x[1], reverse=True)[:4]
        active_total = sum(1 for p in all_panels if not p.get("archived_at"))
        archived_total = len(all_panels) - active_total
        return render_template("portfolio.html",panels=panels,total_panels=active_total,supplier_count=supplier_count,top_spend=top_spend,qualifications=qualifications,classifications=classifications,show_archived=show_archived,archived_total=archived_total)

    @app.route("/panels/new", methods=["GET","POST"])
    def panel_new():
        if request.method == "POST":
            return save_panel()
        return render_template("panel_form.html",panel=None,fields=[])

    @app.route("/panels/<panel_id>/edit", methods=["GET","POST"])
    def panel_edit(panel_id):
        panel = get_panel_or_404(panel_id)
        if request.method == "POST":
            return save_panel(panel)
        return render_template("panel_form.html",panel=panel,fields=panel["data"]["panel"].get("supplierFields",[]))

    def save_panel(existing=None):
        panel_id = request.form.get("panel_id","").strip()
        panel_name = request.form.get("panel_name","").strip()
        category = request.form.get("category","")
        business = request.form.get("business","")
        region_level = request.form.get("region_level","")
        region_value = request.form.get("region_value","").strip()
        owner = request.form.get("owner","").strip()
        mdf_code = request.form.get("mdf_code","")
        if not all([panel_id,panel_name,category,business,region_level,owner,mdf_code]):
            flash("Complete all required panel fields.","error")
            return render_template("panel_form.html",panel=existing,fields=[]),400
        try:
            fields = parse_fields(request.form.get("fields_json","[]"))
        except ValueError as exc:
            flash(str(exc),"error")
            return render_template("panel_form.html",panel=existing,fields=[]),400
        if category not in CATEGORIES or business not in BUSINESSES or region_level not in REGION_LEVELS:
            flash("One or more controlled values are invalid.","error")
            return render_template("panel_form.html",panel=existing,fields=fields),400

        db = get_db()
        suppliers = existing["data"]["panel"].get("suppliers",[]) if existing else []
        created_at = existing["created_at"] if existing else now_iso()
        value = region_value or region_level
        payload = build_panel_payload(panel_id,panel_name,category,business,region_level,value,owner,mdf_code,fields,suppliers,created_at)
        ts = now_iso()
        try:
            if existing:
                db.execute("""UPDATE panels SET panel_name=?,category=?,business=?,region_level=?,region_value=?,owner=?,mdf_code=?,data_json=?,updated_at=? WHERE id=?""",
                           (panel_name,category,business,region_level,value,owner,mdf_code,json.dumps(payload),ts,existing["id"]))
            else:
                db.execute("""INSERT INTO panels(panel_id,panel_name,category,business,region_level,region_value,owner,mdf_code,data_json,created_at,updated_at)
                              VALUES(?,?,?,?,?,?,?,?,?,?,?)""",
                           (panel_id,panel_name,category,business,region_level,value,owner,mdf_code,json.dumps(payload),ts,ts))
            db.commit()
        except sqlite3.IntegrityError:
            flash("Panel ID must be unique.","error")
            return render_template("panel_form.html",panel=existing,fields=fields),409
        flash("Panel saved.","success")
        return redirect(url_for("panel_view",panel_id=panel_id))

    def find_supplier(panel, supplier_id):
        for supplier in panel["data"]["panel"].get("suppliers", []):
            if supplier.get("supplierId") == supplier_id:
                return supplier
        return None

    def append_audit(data, action, supplier_id, details=None):
        data["schemaVersion"] = max(int(data.get("schemaVersion", 1)), 2)
        metadata = data["panel"].setdefault("metadata", {})
        metadata["version"] = max(int(metadata.get("version", 1)), 2)
        metadata["updatedAt"] = now_iso()
        trail = metadata.setdefault("auditTrail", [])
        trail.append({
            "timestamp": now_iso(),
            "action": action,
            "supplierId": supplier_id,
            "details": details or {},
        })

    def save_panel_data(panel, data):
        get_db().execute(
            "UPDATE panels SET data_json=?,updated_at=? WHERE id=?",
            (json.dumps(data), now_iso(), panel["id"]),
        )
        get_db().commit()

    @app.route("/panels/<panel_id>")
    def panel_view(panel_id):
        return render_template("panel_view.html",panel=get_panel_or_404(panel_id))

    @app.route("/panels/<panel_id>/suppliers/new", methods=["GET","POST"])
    def supplier_new(panel_id):
        panel = get_panel_or_404(panel_id)
        if request.method == "POST":
            data = panel["data"]
            suppliers = data["panel"].setdefault("suppliers",[])
            supplier_id = request.form.get("supplier_id","").strip()
            if not supplier_id or any(s["supplierId"] == supplier_id for s in suppliers):
                flash("Supplier ID is required and must be unique within the panel.","error")
                return render_template("supplier_form.html",panel=panel),400
            custom = {}
            for field in data["panel"].get("supplierFields",[]):
                value = request.form.get(f"custom_{field['fieldId']}","")
                if field["type"] == "number" and value != "":
                    try: value = float(value)
                    except ValueError:
                        flash(f"{field['fieldName']} must be numeric.","error")
                        return render_template("supplier_form.html",panel=panel),400
                custom[field["fieldId"]] = value
            suppliers.append({"supplierId":supplier_id,"supplierName":request.form.get("supplier_name","").strip(),"address":request.form.get("address","").strip(),"postCode":request.form.get("post_code","").strip(),"customFields":custom})
            append_audit(data, "supplier_created", supplier_id, {"supplierName": request.form.get("supplier_name","").strip()})
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
                payload = json.loads(raw)
                core = payload["panel"]
                required = ["panelId","panelName","category","business","region","panelOwner","mdfCode","supplierFields","suppliers"]
                if not all(k in core for k in required):
                    raise ValueError("JSON is missing required panel properties.")
                if core["panelId"] != panel_id:
                    raise ValueError("Panel ID cannot be changed from the raw-data editor.")
            except (json.JSONDecodeError,KeyError,TypeError,ValueError) as exc:
                flash(f"JSON not saved: {exc}","error")
                return render_template("data_settings.html",panel=panel,raw_json=raw),400
            core.setdefault("metadata",{})["updatedAt"] = now_iso()
            get_db().execute("UPDATE panels SET data_json=?,updated_at=? WHERE id=?",(json.dumps(payload),now_iso(),panel["id"]))
            get_db().commit()
            flash("Panel JSON updated.","success")
            return redirect(url_for("panel_data",panel_id=panel_id))
        return render_template("data_settings.html",panel=panel,raw_json=json.dumps(panel["data"],indent=2))

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
