"""Weighted supplier scoring; scores are calculated and never stored on suppliers."""
import math


def validate_scoring(raw, fields):
    if not isinstance(raw, list) or len(raw) > 12:
        raise ValueError("Scoring must contain up to 12 criteria.")
    eligible={f["fieldId"]:f for f in fields if f.get("type") in ("stars","number")}
    seen=set()
    clean=[]
    for item in raw:
        if not isinstance(item,dict):
            raise ValueError("Invalid scoring criterion.")
        fid=str(item.get("fieldId",""))
        if fid not in eligible or fid in seen:
            raise ValueError("Scoring criteria must use distinct Number or Stars fields.")
        seen.add(fid)
        try:
            weight=float(item.get("weight",0))
        except (ValueError,TypeError):
            raise ValueError("Scoring weight must be positive.")
        if not math.isfinite(weight) or weight<=0 or weight>1000:
            raise ValueError("Scoring weight must be positive and finite (maximum 1000).")
        clean.append({"fieldId":fid,"weight":weight})
    return clean


def score_suppliers(core):
    criteria=core.get("scoringCriteria",[])
    names={f["fieldId"]:f["fieldName"] for f in core.get("supplierFields",[])}
    total=sum(c["weight"] for c in criteria)
    rows=[]
    for supplier in core.get("suppliers",[]):
        data=supplier.get("customFields",{})
        parts=[]
        weighted_sum=0
        complete=True
        for c in criteria:
            v=data.get(c["fieldId"])
            try:
                n=float(v) if v is not None and v!="" and not isinstance(v,bool) else None
            except (TypeError,ValueError,OverflowError):
                n=None
            if n is None or not math.isfinite(n) or not 0<=n<=5:
                complete=False
                n=None
            else:
                weighted_sum+=n*c["weight"]
            parts.append({"fieldId":c["fieldId"],"name":names.get(c["fieldId"],c["fieldId"]),
                          "weight":c["weight"],"value":n})
        rows.append({"supplierId":supplier.get("supplierId"),"score":round(weighted_sum/total,2) if complete and total else None,
                     "complete":complete and bool(criteria),"parts":parts})
    return rows
