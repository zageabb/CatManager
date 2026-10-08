"""Read-only qualification and action-date alerts."""
from datetime import date, datetime, timedelta


def classify_due_date(raw, today=None, warning_days=30):
    today=today or date.today()
    if raw is None or str(raw).strip()=="":
        return "Missing"
    try:
        due=date.fromisoformat(str(raw).strip()[:10])
    except (TypeError,ValueError):
        return "Invalid"
    if due<today:
        return "Overdue"
    if due<=today+timedelta(days=warning_days):
        return "Due soon"
    return "Future"


def supplier_alerts(core, review_field_id, today=None):
    today=today or date.today()
    results=[]
    for supplier in core.get("suppliers",[]):
        sid=supplier.get("supplierId")
        review=supplier.get("customFields",{}).get(review_field_id)
        status=classify_due_date(review,today)
        items=[]
        for action in supplier.get("actions",[]):
            if action.get("status")=="Completed":
                continue
            due=action.get("dueDate")
            if not due:
                continue
            state=classify_due_date(due,today)
            if state in ("Overdue","Due soon","Invalid"):
                items.append({"title":action.get("title","Action"),"due":due,"status":state})
        results.append({"supplierId":sid,"supplierName":supplier.get("supplierName",sid),
                        "reviewDate":review,"reviewStatus":status,"actions":items})
    return results
