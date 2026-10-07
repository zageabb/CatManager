"""Curated demo data derived from the historical ABB Dynamic Supplier Panel workbook.

The source workbook is not required at runtime. These records intentionally preserve
the old MDF references and supplier-panel fields so the demo resembles the former
Europe Hub panel rather than synthetic sample data.
"""

FIELD_GROUPS = [
    {"groupId": "supplier_profile", "name": "Supplier Profile", "order": 1},
    {"groupId": "risk_qualification", "name": "Risk & Qualification", "order": 2},
    {"groupId": "performance", "name": "Performance", "order": 3},
    {"groupId": "commercial", "name": "Commercial", "order": 4},
    {"groupId": "contact_information", "name": "Contact Information", "order": 5},
]

FIELD_GROUP_BY_ID = {
    "country": "supplier_profile",
    "classification": "supplier_profile",
    "ksm": "supplier_profile",
    "branch_location": "supplier_profile",
    "supplier_risk": "risk_qualification",
    "spe": "risk_qualification",
    "qualification_status": "risk_qualification",
    "hse": "performance",
    "response": "performance",
    "competitiveness": "performance",
    "delivery_time": "performance",
    "quality": "performance",
    "user_experience": "performance",
    "fa_or_price_list": "commercial",
    "turnover_kusd": "commercial",
    "minimum_project_amount_kusd": "commercial",
    "supplier_contact_name": "contact_information",
    "supplier_contact_email": "contact_information",
    "website": "contact_information",
}


def field(field_id, name, field_type="text", order=1):
    return {
        "fieldId": field_id,
        "fieldName": name,
        "type": field_type,
        "options": [],
        "required": False,
        "groupId": FIELD_GROUP_BY_ID.get(field_id, ""),
        "order": order,
    }


COMMON_FIELDS = [
    field("country", "Country", order=1),
    field("classification", "Classification", order=2),
    field("ksm", "KSM", order=3),
    field("supplier_risk", "Supplier Risk", order=4),
    field("spe", "SPE", order=5),
    field("hse", "HSE", "number", 6),
    field("response", "Response", "number", 7),
    field("competitiveness", "Competitiveness", "number", 8),
    field("delivery_time", "Delivery Time", "number", 9),
    field("quality", "Quality", "number", 10),
    field("fa_or_price_list", "FA or Price List", order=11),
    field("user_experience", "User Experience", "number", 12),
    field("supplier_contact_name", "Supplier Contact Name", order=13),
    field("supplier_contact_email", "Supplier Contact Email", order=14),
    field("website", "Website", order=15),
    field("qualification_status", "Qualification Status", order=16),
]


def supplier(supplier_id, name, **custom):
    return {
        "supplierId": supplier_id,
        "supplierName": name,
        "customFields": custom,
    }


def panel(panel_id, sheet, name, category, mdf, suppliers, fields=None):
    effective_fields = fields or COMMON_FIELDS
    used_group_ids = {f.get("groupId") for f in effective_fields if f.get("groupId")}
    field_groups = [dict(g) for g in FIELD_GROUPS if g["groupId"] in used_group_ids]
    return {
        "panelId": panel_id,
        "panelName": name,
        "category": category,
        "business": "GI",
        "region": {"level": "HUB", "value": "Europe"},
        "panelOwner": {"name": "Europe Hub"},
        "leadMdfCode": mdf,
        "mdfCodes": [mdf],
        "fieldGroups": field_groups,
        "supplierFields": effective_fields,
        "suppliers": suppliers,
        "metadata": {
            "legacySource": "Dynamic Supplier Panel 07Sep2021.xlsm",
            "legacySheet": sheet,
            "legacyMdfReference": mdf,
            "demoData": True,
        },
    }


LEGACY_MDF_CODES = {
    "3GX": "Legacy ABB: Power and Distribution Transformers",
    "3JA/B": "Legacy ABB: LV & MV Cables",
    "3FB/I": "Legacy ABB: MV Switchgear",
    "3GB-D": "Legacy ABB: Instrument Transformers",
    "5BC": "Legacy ABB: Civil Works",
    "5BX": "Legacy ABB: Engineering Services",
    "3EH": "Legacy ABB: Protection & Control Relays",
}


LEGACY_DEMO_PANELS = [
    panel(
        "ABB-3GX", "3GX", "Power and Distribution Transformers", "Transformers", "3GX",
        [
            supplier(
                "G02197242", "Koncar Power Transformers Ltd.",
                country="Croatia", classification="2. HBU Preferred", ksm="Emre Gul",
                supplier_risk="Medium", spe="", hse=3.0, response=4.0,
                competitiveness="", delivery_time="", quality="", fa_or_price_list="",
                user_experience="", supplier_contact_name="Branka Babickovic",
                supplier_contact_email="branka.babickovic@koncar-dst.hr",
                website="https://kpt.hr/en/",
            ),
            supplier(
                "G01021821", "TAMINI Transformatori S.r.l.",
                country="Italy", classification="2. HBU Preferred", ksm="Emre Gül",
                supplier_risk="", spe="", hse="", response="", competitiveness="",
                delivery_time="", quality="", fa_or_price_list="", user_experience="",
                supplier_contact_name="Andrea Longhi",
                supplier_contact_email="a.longhi@tamini.it", website="www.tamini.it",
            ),
        ],
    ),
    panel(
        "ABB-3JA", "3JA", "LV & MV Cables", "Cables & Conductors", "3JA/B",
        [
            supplier(
                "G04801948", "NEXANS ELLAS SA",
                country="Greece", classification="2. HBU Preferred", ksm="Lilika Zerva",
                supplier_risk="Medium", spe="", hse=4.0, response=2.5,
                competitiveness=3.0, delivery_time=2.0, quality=3.0,
                fa_or_price_list="Global FA", user_experience="",
                supplier_contact_name="Lothar Wilms",
                supplier_contact_email="Lothar.Wilms@nexans.com",
                website="https://www.nexans.com/",
            ),
            supplier(
                "G06891605", "Nexans Italia S.p.A.",
                country="Italy", classification="2. HBU Preferred", ksm="Lilika Zerva",
                supplier_risk="Low", spe="", hse="", response="", competitiveness="",
                delivery_time="", quality="", fa_or_price_list="Global FA",
                user_experience="", supplier_contact_name="", supplier_contact_email="",
                website="https://www.nexans.com/",
            ),
        ],
    ),
    panel(
        "ABB-MVSWG", "MVSWG", "MV Switchgear", "Switchgear", "3FB/I",
        [
            supplier(
                "G02000757", "Ormazabal",
                country="Spain", classification="3. Country Preferred", ksm="Emre Gül",
                supplier_risk="Low", spe="", hse="", response=5.0, competitiveness=4.0,
                delivery_time=4.0, quality=4.0, fa_or_price_list="",
                user_experience=1, supplier_contact_name="Juncal Gorostiza Fernandez",
                supplier_contact_email="gof@ormazabal.com", website="",
            ),
            supplier(
                "LEGACY-ULUSOY", "Ulusoy - Eaton",
                country="Turkey", classification="3. Country Preferred", ksm="Emre Gül",
                supplier_risk="", spe="", hse="", response=4.0, competitiveness=4.0,
                delivery_time=4.0, quality="", fa_or_price_list="", user_experience=1,
                supplier_contact_name="Çağdaş Yüksel",
                supplier_contact_email="cagdasyuksel@eaton.com", website="",
            ),
        ],
    ),
    panel(
        "ABB-IT", "IT", "Instrument Transformers", "Current Transformers", "3GB-D",
        [
            supplier(
                "G07025702", "Electrotecnica Arteche Hermanos",
                country="Spain", classification="2. HBL Preferred", ksm="Manuela Escobar",
                supplier_risk="Low", spe="", hse=4.3, response=4.3, competitiveness=4.0,
                delivery_time=2.3, quality=4.3, fa_or_price_list="", user_experience="",
                supplier_contact_name="", supplier_contact_email="", website="",
            ),
            supplier(
                "G04623055", "Koncar Instrument Transformers",
                country="Croatia", classification="2. HBL Preferred", ksm="Giorgos Apostolou",
                supplier_risk="Medium", spe="", hse=4.0, response=5.0, competitiveness=4.0,
                delivery_time=4.0, quality=4.0, fa_or_price_list="", user_experience="",
                supplier_contact_name="", supplier_contact_email="", website="",
            ),
        ],
    ),
    panel(
        "ABB-CIV", "CIV", "Civil Works", "Civil Engineering", "5BC", [],
        fields=[
            field("country", "Country", order=1),
            field("branch_location", "Branch Location (city)", order=2),
            field("turnover_kusd", "Turnover (kUSD)", "number", 3),
            field("minimum_project_amount_kusd", "Minimum Project Amount (kUSD)", "number", 4),
            field("classification", "Classification", order=5),
            field("ksm", "KSM", order=6),
            field("supplier_risk", "Supplier Risk", order=7),
            field("spe", "SPE", order=8),
        ],
    ),
    panel(
        "ABB-ENG", "ENG", "Engineering Services", "Services", "5BX",
        [
            supplier(
                "G08026844", "Izharia Ingenieria Y Consultoria Sl",
                country="Spain", classification="3. Country Preferred", ksm="Manuela Escobar",
                supplier_risk="Low", spe="", hse="", response="", competitiveness="",
                delivery_time="", quality="", fa_or_price_list="", user_experience="",
                supplier_contact_name="David Navarro",
                supplier_contact_email="dnavarro@izharia.com", website="",
            ),
            supplier(
                "G35036566", "Zetacero Servicios Arquitectura E Ingenieria S.L.",
                country="Spain", classification="3. Country Preferred", ksm="Manuela Escobar",
                supplier_risk="", spe="", hse=4.0, response=5.0, competitiveness=4.0,
                delivery_time=5.0, quality=4.0, fa_or_price_list="", user_experience=1,
                supplier_contact_name="Luis Montalban",
                supplier_contact_email="lmontalban@zetacero.com", website="",
            ),
        ],
    ),
    panel(
        "ABB-3EH", "3EH", "Protection & Control Relays", "Protection & Control", "3EH",
        [
            supplier(
                "G08050144", "TE Connectivity Amp España SL.",
                country="Spain", classification="2. HBL Preferred", ksm="Carlos Sousa",
                supplier_risk="Low", spe="", hse="", response="", competitiveness="",
                delivery_time="", quality="", fa_or_price_list="", user_experience="",
                supplier_contact_name="", supplier_contact_email="", website="",
            ),
            supplier(
                "G01021891", "GE Power Management S.L.",
                country="Spain", classification="3. Country Preferred", ksm="Ruth-Garcia Alcaide",
                supplier_risk="Low", spe="", hse=4.0, response=4.0, competitiveness=4.0,
                delivery_time=3.0, quality=4.0, fa_or_price_list="", user_experience=1,
                supplier_contact_name="", supplier_contact_email="", website="",
            ),
        ],
    ),
]
