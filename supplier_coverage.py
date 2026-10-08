"""Read-only regional coverage and source concentration for one panel.

MDFs are assigned at panel level, not to suppliers, so MDF coverage is reported
as panel scope only and not misrepresented as supplier capability.
"""

def coverage_summary(core, qualification_field="qualification_status"):
    fields=[f for f in core.get("supplierFields",[]) if f.get("type")=="multiselect_blocks"]
    suppliers=core.get("suppliers",[])
    groups=[]
    for field in fields:
        options=list(dict.fromkeys(field.get("options",[])))
        rows=[]
        for option in options:
            covered=[]
            qualified=[]
            for supplier in suppliers:
                selections=supplier.get("customFields",{}).get(field["fieldId"],[])
                if not isinstance(selections,list) or option not in selections:
                    continue
                covered.append(supplier)
                if str(supplier.get("customFields",{}).get(qualification_field,"")).casefold()=="qualified":
                    qualified.append(supplier)
            count=len(covered)
            rows.append({"region":option,"count":count,"qualifiedCount":len(qualified),
                         "supplierIds":[s["supplierId"] for s in covered],
                         "risk":"Uncovered" if count==0 else "Single source" if count==1 else "Multiple sources"})
        groups.append({"fieldId":field["fieldId"],"fieldName":field["fieldName"],"regions":rows})
    return {"groups":groups,"mdfCodes":core.get("mdfCodes",[]),
            "leadMdfCode":core.get("leadMdfCode",core.get("mdfCode","")),
            "supplierCount":len(suppliers)}
