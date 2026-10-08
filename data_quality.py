"""Read-only validation of CatManager supplier and panel data."""
import math
from datetime import date


def inspect_panel(core):
    findings=[]
    fields=core.get("supplierFields",[])
    by_id={f.get("fieldId"):f for f in fields}
    def flag(code,message,supplier_id=None,field_id=None):
        findings.append({"code":code,"message":message,
                         "supplierId":supplier_id,"fieldId":field_id})
    for widget in core.get("dashboardWidgets",[]):
        for key in ("fieldId","otherFieldId"):
            fid=widget.get(key)
            if fid and fid not in by_id and fid not in ("supplierId","supplierName"):
                flag("broken_widget",f"KPI {widget.get('title','')} references unavailable field {fid}.",field_id=fid)
    for criterion in core.get("scoringCriteria",[]):
        fid=criterion.get("fieldId")
        if fid not in by_id or by_id[fid].get("type") not in ("stars","number"):
            flag("broken_score",f"Weighted scoring references invalid field {fid}.",field_id=fid)
    for supplier in core.get("suppliers",[]):
        sid=supplier.get("supplierId")
        if not str(sid or "").strip():
            flag("missing_identity","Missing Supplier ID.",sid)
        if not str(supplier.get("supplierName") or "").strip():
            flag("missing_identity","Missing supplier name.",sid)
        custom=supplier.get("customFields",{}) or {}
        for field in fields:
            fid=field.get("fieldId")
            val=custom.get(fid)
            empty=val is None or val=="" or val==[]
            if field.get("required") and empty:
                flag("missing_required",f"Required field {field.get('fieldName',fid)} is missing.",sid,fid)
                continue
            if empty:continue
            kind=field.get("type")
            if kind in ("number","stars"):
                try:
                    value=float(val)
                    valid=not isinstance(val,bool) and math.isfinite(value)
                    if kind=="stars":
                        valid=valid and 0<=value<=5 and value*2==int(value*2)
                except (TypeError,ValueError,OverflowError):
                    valid=False
                if not valid:flag("invalid_value",f"Invalid {kind} value in {field.get('fieldName',fid)}.",sid,fid)
            if kind=="multiselect_blocks" and (not isinstance(val,list) or any(v not in field.get("options",[]) for v in val)):
                flag("invalid_region",f"Invalid coverage selection for {field.get('fieldName',fid)}.",sid,fid)
        for fid in custom:
            if fid not in by_id:
                flag("orphan_value",f"Supplier has value for undefined field {fid}.",sid,fid)
    return findings


def collect_quality(panels):
    records=[]
    for panel in panels:
        findings=inspect_panel(panel["data"]["panel"])
        records.append({"panelId":panel["panel_id"],"panelName":panel["panel_name"],
                        "archived":bool(panel.get("archived_at")),"findings":findings})
    return records
