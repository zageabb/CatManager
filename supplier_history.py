"""Read-only supplier changes reconstructed only from recorded audit evidence."""
def _diff(before, after, prefix=""):
    before=before if isinstance(before,dict) else {}
    after=after if isinstance(after,dict) else {}
    out=[]
    for key in sorted(set(before)|set(after)):
        a,b=before.get(key),after.get(key)
        if a==b:continue
        if isinstance(a,dict) or isinstance(b,dict):
            out.extend(_diff(a,b,prefix+key+"."))
        else:
            out.append({"field":prefix+key,"before":a,"after":b})
    return out


def supplier_history(core, supplier_id):
    fields={f["fieldId"]:f for f in core.get("supplierFields",[])}
    events=[]
    for event in core.get("metadata",{}).get("auditTrail",[]):
        action=event.get("action","")
        details=event.get("details",{})
        before=after=None
        if action=="supplier_updated" and event.get("entityId")==supplier_id:
            before=details.get("before");after=details.get("after")
        elif action in ("supplier_bulk_custom_fields_updated","supplier_excel_import"):
            change=next((x for x in details.get("changes",[]) if x.get("supplierId")==supplier_id),None)
            if change:
                before={"customFields":change.get("before",{})}
                after={"customFields":change.get("after",{})}
        elif action in ("supplier_action_created","supplier_action_updated") and event.get("entityId")==supplier_id:
            before={"action":details.get("before") or {}}
            after={"action":details.get("after") or {}}
        if after is None:continue
        changes=_diff(before,after)
        if not changes:continue
        for entry in changes:
            if entry["field"].startswith("customFields."):
                fid=entry["field"].split(".",1)[1]
                entry["label"]=fields.get(fid,{}).get("fieldName",fid)
            else:
                entry["label"]=entry["field"]
        events.append({"timestamp":event.get("timestamp",""),"actor":event.get("actor",""),
                       "action":action,"changes":changes})
    events.sort(key=lambda x:x["timestamp"],reverse=True)
    trends=[]
    for fid,field in fields.items():
        if field.get("type") not in ("number","stars"):continue
        points=[]
        for event in reversed(events):
            for change in event["changes"]:
                if change["field"]!="customFields."+fid:continue
                try:
                    value=float(change["after"])
                    if value==value and abs(value)!=float("inf"):
                        points.append({"timestamp":event["timestamp"],"value":value})
                except (ValueError,TypeError,OverflowError):
                    pass
        if points:trends.append({"fieldId":fid,"label":field["fieldName"],"points":points})
    return {"events":events,"trends":trends}
