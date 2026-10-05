import io
from datetime import datetime, timedelta, timezone
import json
import pytest
from app import create_app

@pytest.fixture()
def app(tmp_path):
    return create_app({"TESTING": True, "DATABASE": str(tmp_path / "test.sqlite"), "SEED_DEMO": False, "SECRET_KEY": "test"})

@pytest.fixture()
def client(app):
    return app.test_client()

def create_panel(client, panel_id="CMP1000"):
    return client.post("/panels/new", data={
        "panel_id": panel_id,
        "panel_name": "Test Transformers",
        "category": "Transformers",
        "business": "GI",
        "region_level": "Country",
        "region_value": "United Kingdom",
        "owner": "Test Owner",
        "mdf_codes": ["MDF-TR-001"],
        "lead_mdf_code": "MDF-TR-001",
        "fields_json": json.dumps([{"fieldId":"rating","fieldName":"Rating","type":"number","required":False,"options":[]}]),
    })

def test_empty_portfolio(client):
    response=client.get("/")
    assert response.status_code==200
    assert b"Category panel" in response.data

def test_create_panel_and_api(client):
    response=create_panel(client)
    assert response.status_code==302
    api=client.get("/api/panels/CMP1000")
    assert api.status_code==200
    body=api.get_json()
    assert body["panel"]["panelName"]=="Test Transformers"
    assert body["panel"]["region"]["value"]=="United Kingdom"
    assert body["panel"]["supplierFields"][0]["fieldId"]=="rating"

def test_duplicate_panel_id_rejected(client):
    create_panel(client)
    response=create_panel(client)
    assert response.status_code==409

def test_add_supplier_uses_custom_schema(client):
    create_panel(client)
    response=client.post("/panels/CMP1000/suppliers/new", data={"supplier_id":"SUP-1","supplier_name":"Supplier One","address":"Road","post_code":"AA1 1AA","custom_rating":"250"})
    assert response.status_code==302
    body=client.get("/api/panels/CMP1000").get_json()
    supplier=body["panel"]["suppliers"][0]
    assert supplier["supplierId"]=="SUP-1"
    assert supplier["customFields"]["rating"]==250.0

def test_raw_json_rejects_panel_id_change(client):
    create_panel(client)
    payload=client.get("/api/panels/CMP1000").get_json()
    payload["panel"]["panelId"]="OTHER"
    response=client.post("/panels/CMP1000/data", data={"raw_json":json.dumps(payload)})
    assert response.status_code==400


def test_edit_supplier_preserves_id_and_records_audit(client):
    create_panel(client)
    client.post("/panels/CMP1000/suppliers/new", data={
        "supplier_id":"SUP-1","supplier_name":"Supplier One","address":"Road","post_code":"AA1 1AA","custom_rating":"250"
    })
    response=client.post("/panels/CMP1000/suppliers/SUP-1/edit", data={
        "supplier_id":"SUP-1","supplier_name":"Supplier Updated","address":"New Road","post_code":"BB2 2BB","custom_rating":"300"
    })
    assert response.status_code==302
    body=client.get("/api/panels/CMP1000").get_json()
    supplier=body["panel"]["suppliers"][0]
    assert supplier["supplierId"]=="SUP-1"
    assert supplier["supplierName"]=="Supplier Updated"
    assert supplier["customFields"]["rating"]==300.0
    audit=body["panel"]["metadata"]["auditTrail"]
    assert audit[-1]["action"]=="supplier_updated"
    assert audit[-1]["details"]["before"]["supplierName"]=="Supplier One"

def test_delete_supplier_requires_exact_confirmation_and_keeps_snapshot(client):
    create_panel(client)
    client.post("/panels/CMP1000/suppliers/new", data={
        "supplier_id":"SUP-1","supplier_name":"Supplier One","address":"Road","post_code":"AA1 1AA","custom_rating":"250"
    })
    refused=client.post("/panels/CMP1000/suppliers/SUP-1/delete", data={"confirm_supplier_id":"wrong"})
    assert refused.status_code==302
    body=client.get("/api/panels/CMP1000").get_json()
    assert len(body["panel"]["suppliers"])==1

    accepted=client.post("/panels/CMP1000/suppliers/SUP-1/delete", data={"confirm_supplier_id":"SUP-1"})
    assert accepted.status_code==302
    body=client.get("/api/panels/CMP1000").get_json()
    assert body["panel"]["suppliers"]==[]
    audit=body["panel"]["metadata"]["auditTrail"]
    assert audit[-1]["action"]=="supplier_deleted"
    assert audit[-1]["details"]["snapshot"]["supplierId"]=="SUP-1"


def test_archive_panel_requires_confirmation_and_is_reversible(client):
    create_panel(client)
    refused=client.post("/panels/CMP1000/archive", data={"confirm_panel_id":"wrong"})
    assert refused.status_code==302
    assert client.get("/api/panels/CMP1000").status_code==200
    assert b"CMP1000" in client.get("/").data

    archived=client.post("/panels/CMP1000/archive", data={"confirm_panel_id":"CMP1000"})
    assert archived.status_code==302
    active_page=client.get("/").data
    archived_page=client.get("/?archived=1").data
    assert b'href="/panels/CMP1000"' not in active_page
    assert b'href="/panels/CMP1000"' in archived_page
    body=client.get("/api/panels/CMP1000").get_json()
    assert body["panel"]["metadata"]["status"]=="archived"
    assert body["panel"]["metadata"]["auditTrail"][-1]["action"]=="panel_archived"

    restored=client.post("/panels/CMP1000/restore")
    assert restored.status_code==302
    assert b"CMP1000" in client.get("/").data
    body=client.get("/api/panels/CMP1000").get_json()
    assert body["panel"]["metadata"]["status"]=="active"
    assert body["panel"]["metadata"]["auditTrail"][-1]["action"]=="panel_restored"


def test_mdf_master_data_admin_and_usage_guard(client):
    page=client.get("/settings/mdf")
    assert page.status_code==200
    assert b"MDF-TR-001" in page.data

    added=client.post("/settings/mdf", data={"code":"MDF-NEW-001","description":"New Equipment"})
    assert added.status_code==302
    page=client.get("/settings/mdf")
    assert b"MDF-NEW-001" in page.data
    assert b"New Equipment" in page.data

    create_panel(client)
    blocked=client.post("/settings/mdf/MDF-TR-001/toggle")
    assert blocked.status_code==302
    page=client.get("/settings/mdf")
    assert b"used by 1 active panel" in page.data

    deactivated=client.post("/settings/mdf/MDF-NEW-001/toggle")
    assert deactivated.status_code==302
    new_panel=client.get("/panels/new")
    assert b'value="MDF-NEW-001"' not in new_panel.data

    reactivated=client.post("/settings/mdf/MDF-NEW-001/toggle")
    assert reactivated.status_code==302
    new_panel=client.get("/panels/new")
    assert b'value="MDF-NEW-001"' in new_panel.data


def test_panel_supports_multiple_mdf_codes(client):
    response=client.post("/panels/new", data={
        "panel_id":"CMP2000",
        "panel_name":"Multi MDF Panel",
        "category":"Transformers",
        "business":"GI",
        "region_level":"Global",
        "region_value":"Global",
        "owner":"Owner",
        "mdf_codes":["MDF-TR-001","3GF"],
        "lead_mdf_code":"MDF-TR-001",
        "fields_json":"[]",
    })
    assert response.status_code==302
    body=client.get("/api/panels/CMP2000").get_json()
    assert body["panel"]["leadMdfCode"]=="MDF-TR-001"
    assert set(body["panel"]["mdfCodes"])=={"MDF-TR-001","3GF"}
    assert body["panel"]["mdfCode"]=="MDF-TR-001"

def test_lead_mdf_must_be_selected(client):
    response=client.post("/panels/new", data={
        "panel_id":"CMP2001",
        "panel_name":"Invalid MDF Panel",
        "category":"Transformers",
        "business":"GI",
        "region_level":"Global",
        "region_value":"Global",
        "owner":"Owner",
        "mdf_codes":["3GF"],
        "lead_mdf_code":"MDF-TR-001",
        "fields_json":"[]",
    })
    assert response.status_code==400


def test_new_custom_field_can_be_amended_by_supplier_form_and_bulk_editor(client):
    create_panel(client)
    client.post("/panels/CMP1000/suppliers/new", data={
        "supplier_id":"SUP-1",
        "supplier_name":"Supplier One",
        "address":"Road",
        "post_code":"AA1 1AA",
        "custom_rating":"250",
    })

    updated_panel=client.post("/panels/CMP1000/edit", data={
        "panel_id":"CMP1000",
        "panel_name":"Test Transformers",
        "category":"Transformers",
        "business":"GI",
        "region_level":"Country",
        "region_value":"United Kingdom",
        "owner":"Test Owner",
        "mdf_codes":["MDF-TR-001"],
        "lead_mdf_code":"MDF-TR-001",
        "fields_json":json.dumps([
            {"fieldId":"rating","fieldName":"Rating","type":"number","required":False,"options":[]},
            {"fieldId":"review_status","fieldName":"Review Status","type":"dropdown","required":False,"options":["Open","Closed"]},
        ]),
    })
    assert updated_panel.status_code==302

    supplier_form=client.get("/panels/CMP1000/suppliers/SUP-1/edit")
    assert supplier_form.status_code==200
    assert b"Review Status" in supplier_form.data

    panel_view=client.get("/panels/CMP1000")
    assert b'/panels/CMP1000/suppliers/SUP-1/edit' in panel_view.data
    assert b"Edit supplier data" in panel_view.data

    bulk_page=client.get("/panels/CMP1000/suppliers/bulk-edit")
    assert bulk_page.status_code==200
    assert b"Review Status" in bulk_page.data
    assert b"Supplier One" in bulk_page.data

    saved=client.post("/panels/CMP1000/suppliers/bulk-edit", data={
        "SUP-1__rating":"275",
        "SUP-1__review_status":"Open",
    })
    assert saved.status_code==302
    body=client.get("/api/panels/CMP1000").get_json()
    supplier=body["panel"]["suppliers"][0]
    assert supplier["supplierName"]=="Supplier One"
    assert supplier["address"]=="Road"
    assert supplier["postCode"]=="AA1 1AA"
    assert supplier["customFields"]["rating"]==275.0
    assert supplier["customFields"]["review_status"]=="Open"
    assert body["panel"]["metadata"]["auditTrail"][-1]["action"]=="supplier_bulk_custom_fields_updated"


def test_mdf_selector_is_searchable_compact_multiselect(client):
    page=client.get("/panels/new")
    assert page.status_code==200
    assert b"mdf-select-trigger" in page.data
    assert b"Search MDF code or description" in page.data
    assert b"mdf-check-grid" not in page.data
    assert b'value="3AA"' in page.data
    assert b'value="5BZ"' in page.data

def test_uploaded_mdf_catalogue_is_loaded(client):
    page=client.get("/settings/mdf")
    assert page.status_code==200
    assert b"Terminal Blocks" in page.data
    assert b"Offshore Route Preparation Services" in page.data


def test_portfolio_favourites_sorting_pagination_and_persistent_filters(client):
    for idx in range(12):
        response=client.post("/panels/new", data={
            "panel_id":f"CMP3{idx:03d}",
            "panel_name":f"Panel {chr(65 + (11-idx))}",
            "category":"Transformers" if idx % 2 == 0 else "Switchgear",
            "business":"GI" if idx % 2 == 0 else "GPQSS",
            "region_level":"Country",
            "region_value":"United Kingdom",
            "owner":f"Owner {idx:02d}",
            "mdf_codes":["MDF-TR-001"],
            "lead_mdf_code":"MDF-TR-001",
            "fields_json":"[]",
        })
        assert response.status_code==302

    fav=client.post("/panels/CMP3000/favourite", data={"return_to":"/"})
    assert fav.status_code==302
    favourites=client.get("/?favourites=1")
    assert b"CMP3000" in favourites.data
    assert b"CMP3001" not in favourites.data

    page=client.get("/?category=Transformers&business=GI&q=Panel&page_size=10&sort=panel&direction=asc")
    assert page.status_code==200
    assert b"Page 1 of" in page.data
    assert b"10 rows" in page.data
    first_pos=page.data.find(b"Panel B")
    later_pos=page.data.find(b"Panel D")
    assert first_pos != -1 and later_pos != -1 and first_pos < later_pos

    with client.session_transaction() as sess:
        saved=sess["portfolio_filters"]
        assert saved["category"]=="Transformers"
        assert saved["business"]=="GI"
        assert saved["q"]=="Panel"
        assert saved["sort"]=="panel"
        assert saved["direction"]=="asc"

    persisted=client.get("/")
    assert b'value="Panel"' in persisted.data
    assert b"Transformers" in persisted.data

    reset=client.get("/?clear=1", follow_redirects=True)
    assert reset.status_code==200
    with client.session_transaction() as sess:
        assert "portfolio_filters" not in sess

def test_portfolio_paginates_large_result_sets(client):
    for idx in range(11):
        response=client.post("/panels/new", data={
            "panel_id":f"CMP4{idx:03d}",
            "panel_name":f"Paged Panel {idx:02d}",
            "category":"Transformers",
            "business":"GI",
            "region_level":"Global",
            "region_value":"Global",
            "owner":"Owner",
            "mdf_codes":["MDF-TR-001"],
            "lead_mdf_code":"MDF-TR-001",
            "fields_json":"[]",
        })
        assert response.status_code==302
    first=client.get("/?q=Paged+Panel&page_size=10&sort=panel&direction=asc")
    second=client.get("/?q=Paged+Panel&page_size=10&sort=panel&direction=asc&page=2")
    assert b"Page 1 of 2" in first.data
    assert b"Page 2 of 2" in second.data
    assert b"CMP4010" in second.data


def test_supplier_master_import_generates_addresses_and_supports_typeahead(client):
    csv_data = b"BPID,Supplier_Name\n1000000001,Alpha Engineering\n1000000002,Beta Power Ltd\n"
    response = client.post(
        "/settings/suppliers",
        data={"supplier_file": (io.BytesIO(csv_data), "suppliers.csv")},
        content_type="multipart/form-data",
    )
    assert response.status_code == 302

    search = client.get("/api/supplier-master/search?q=Alpha")
    assert search.status_code == 200
    rows = search.get_json()
    assert rows[0]["bpid"] == "1000000001"
    assert rows[0]["supplier_name"] == "Alpha Engineering"
    assert rows[0]["address"]
    assert rows[0]["post_code"]
    assert rows[0]["address_source"] == "generated"

    by_bpid = client.get("/api/supplier-master/search?q=1000000002")
    assert by_bpid.get_json()[0]["supplier_name"] == "Beta Power Ltd"

    form = client.get("/panels/new")
    assert form.status_code == 200

def test_supplier_master_remove_hides_from_selection_but_can_restore(client):
    csv_data = b"BPID,Supplier_Name\n1000000010,Remove Me Ltd\n"
    client.post(
        "/settings/suppliers",
        data={"supplier_file": (io.BytesIO(csv_data), "suppliers.csv")},
        content_type="multipart/form-data",
    )
    assert client.get("/api/supplier-master/search?q=Remove").get_json()

    removed = client.post("/settings/suppliers/1000000010/remove")
    assert removed.status_code == 302
    assert client.get("/api/supplier-master/search?q=Remove").get_json() == []

    removed_page = client.get("/settings/suppliers?removed=1&q=Remove")
    assert b"Remove Me Ltd" in removed_page.data
    assert b"Removed" in removed_page.data

    restored = client.post("/settings/suppliers/1000000010/restore")
    assert restored.status_code == 302
    assert client.get("/api/supplier-master/search?q=Remove").get_json()

def test_add_supplier_uses_master_data_when_bpid_selected(client):
    create_panel(client)
    csv_data = b"BPID,Supplier_Name,Address,Post_Code\n1000000020,Master Supplier Ltd,1 Real Road,AB1 2CD\n"
    client.post(
        "/settings/suppliers",
        data={"supplier_file": (io.BytesIO(csv_data), "suppliers.csv")},
        content_type="multipart/form-data",
    )
    response = client.post("/panels/CMP1000/suppliers/new", data={
        "supplier_id":"1000000020",
        "supplier_name":"Wrong Manual Name",
        "address":"Wrong Address",
        "post_code":"ZZ1 1ZZ",
        "custom_rating":"123",
    })
    assert response.status_code == 302
    supplier = client.get("/api/panels/CMP1000").get_json()["panel"]["suppliers"][0]
    assert supplier["supplierName"] == "Master Supplier Ltd"
    assert supplier["address"] == "1 Real Road"
    assert supplier["postCode"] == "AB1 2CD"
    assert supplier["masterLinked"] is True

def test_supplier_form_contains_master_typeahead(client):
    create_panel(client)
    page = client.get("/panels/CMP1000/suppliers/new")
    assert page.status_code == 200
    assert b"Find supplier by BPID or name" in page.data
    assert b"supplier-master-search" in page.data


def test_dashboard_uses_configured_currency_and_review_semantics(client):
    fields = [
        {"fieldId":"annual_spend","fieldName":"Annual Spend","type":"number","required":False,"options":[]},
        {"fieldId":"spend_currency","fieldName":"Spend Currency","type":"dropdown","required":False,"options":["GBP","EUR","USD"]},
        {"fieldId":"qualification_status","fieldName":"Qualification Status","type":"dropdown","required":False,"options":["Qualified","In review"]},
        {"fieldId":"qualification_review_date","fieldName":"Qualification Review Date","type":"date","required":False,"options":[]},
        {"fieldId":"classification","fieldName":"Classification","type":"dropdown","required":False,"options":["Preferred","Standard"]},
    ]
    response=client.post("/panels/new", data={
        "panel_id":"CMP5000",
        "panel_name":"Dashboard Panel",
        "category":"Transformers",
        "business":"GI",
        "region_level":"Global",
        "region_value":"Global",
        "owner":"Owner",
        "mdf_codes":["MDF-TR-001"],
        "lead_mdf_code":"MDF-TR-001",
        "fields_json":json.dumps(fields),
    })
    assert response.status_code==302

    today=datetime.now(timezone.utc).date()
    suppliers=[
        ("SUP-D1","Alpha Supplier","1000000","GBP","Qualified",(today-timedelta(days=1)).isoformat(),"Preferred"),
        ("SUP-D2","Alpha Supplier","2000000","EUR","In review",(today+timedelta(days=10)).isoformat(),"Standard"),
        ("SUP-D3","Gamma Supplier","3000000","USD","Qualified","", "Preferred"),
    ]
    for sid,name,spend,currency,qual,review,classification in suppliers:
        response=client.post("/panels/CMP5000/suppliers/new", data={
            "supplier_id":sid,
            "supplier_name":name,
            "address":"Road",
            "post_code":"AA1 1AA",
            "custom_annual_spend":spend,
            "custom_spend_currency":currency,
            "custom_qualification_status":qual,
            "custom_qualification_review_date":review,
            "custom_classification":classification,
        })
        assert response.status_code==302

    settings=client.post("/settings/dashboard", data={
        "base_currency":"GBP",
        "spend_field_id":"annual_spend",
        "currency_field_id":"spend_currency",
        "qualification_field_id":"qualification_status",
        "qualification_review_field_id":"qualification_review_date",
        "classification_field_id":"classification",
        "currency_rates":"GBP=1\nEUR=0.5",
    })
    assert settings.status_code==302

    page=client.get("/")
    assert page.status_code==200
    assert b"GBP 2.0M" in page.data
    assert b"USD 3,000,000" in page.data
    assert b"Alpha Supplier" in page.data
    assert b"2</strong>" in page.data
    assert b"1 overdue" in page.data
    assert b"Due in 30 days" in page.data
    assert b"No review date" in page.data

def test_dashboard_settings_reject_invalid_currency_rates(client):
    response=client.post("/settings/dashboard", data={
        "base_currency":"GBP",
        "spend_field_id":"annual_spend",
        "currency_field_id":"spend_currency",
        "qualification_field_id":"qualification_status",
        "qualification_review_field_id":"qualification_review_date",
        "classification_field_id":"classification",
        "currency_rates":"GBP=1\nEUR=not-a-number",
    })
    assert response.status_code==400
    assert b"Currency rates must use" in response.data


def test_field_removal_previews_impact_preserves_orphan_and_allows_restore_or_purge(client):
    create_panel(client)
    client.post("/panels/CMP1000/suppliers/new", data={
        "supplier_id":"SUP-ORPHAN",
        "supplier_name":"Orphan Supplier",
        "address":"Road",
        "post_code":"AA1 1AA",
        "custom_rating":"250",
    })
    edit_data={
        "panel_id":"CMP1000",
        "panel_name":"Test Transformers",
        "category":"Transformers",
        "business":"GI",
        "region_level":"Country",
        "region_value":"United Kingdom",
        "owner":"Test Owner",
        "mdf_codes":["MDF-TR-001"],
        "lead_mdf_code":"MDF-TR-001",
        "fields_json":"[]",
    }

    preview=client.post("/panels/CMP1000/edit", data=edit_data)
    assert preview.status_code==409
    assert b"Field removal impact" in preview.data
    assert b"Rating" in preview.data
    assert b"SUP-ORPHAN" in preview.data

    before=client.get("/api/panels/CMP1000").get_json()
    assert before["panel"]["supplierFields"][0]["fieldId"]=="rating"
    assert before["panel"]["suppliers"][0]["customFields"]["rating"]==250.0

    confirmed=client.post("/panels/CMP1000/edit", data={**edit_data,"confirm_field_removal":"1"})
    assert confirmed.status_code==302
    body=client.get("/api/panels/CMP1000").get_json()
    assert body["panel"]["supplierFields"]==[]
    assert body["panel"]["suppliers"][0]["customFields"]["rating"]==250.0
    orphan=body["panel"]["metadata"]["orphanedSupplierFields"]["rating"]
    assert orphan["field"]["fieldName"]=="Rating"
    assert orphan["affectedSuppliers"]==1

    orphan_page=client.get("/panels/CMP1000/fields/orphans")
    assert orphan_page.status_code==200
    assert b"Orphan Supplier" in orphan_page.data
    assert b"250.0" in orphan_page.data

    restored=client.post("/panels/CMP1000/fields/orphans/rating/restore")
    assert restored.status_code==302
    restored_body=client.get("/api/panels/CMP1000").get_json()
    assert restored_body["panel"]["supplierFields"][0]["fieldId"]=="rating"
    assert "rating" not in restored_body["panel"]["metadata"]["orphanedSupplierFields"]

    client.post("/panels/CMP1000/edit", data=edit_data)
    client.post("/panels/CMP1000/edit", data={**edit_data,"confirm_field_removal":"1"})
    refused=client.post("/panels/CMP1000/fields/orphans/rating/purge", data={"confirm_field_id":"wrong"})
    assert refused.status_code==302
    assert "rating" in client.get("/api/panels/CMP1000").get_json()["panel"]["suppliers"][0]["customFields"]

    purged=client.post("/panels/CMP1000/fields/orphans/rating/purge", data={"confirm_field_id":"rating"})
    assert purged.status_code==302
    purged_body=client.get("/api/panels/CMP1000").get_json()
    assert "rating" not in purged_body["panel"]["suppliers"][0]["customFields"]
    assert "rating" not in purged_body["panel"]["metadata"]["orphanedSupplierFields"]
    assert purged_body["panel"]["metadata"]["auditTrail"][-1]["action"]=="orphan_field_purged"


def test_panel_import_migrates_v1_and_export_returns_current_schema(client):
    legacy={
        "schemaVersion":1,
        "panel":{
            "panelId":"CMP6000",
            "panelName":"Legacy Import",
            "category":"Transformers",
            "business":"GI",
            "region":{"level":"Global","value":"Global"},
            "panelOwner":{"name":"Owner"},
            "mdfCode":"MDF-TR-001",
            "supplierFields":[],
            "suppliers":[],
        },
    }
    response=client.post(
        "/panels/import",
        data={"panel_file":(io.BytesIO(json.dumps(legacy).encode("utf-8")),"legacy.json")},
        content_type="multipart/form-data",
    )
    assert response.status_code==302
    body=client.get("/api/panels/CMP6000").get_json()
    assert body["schemaVersion"]==3
    assert body["panel"]["leadMdfCode"]=="MDF-TR-001"
    assert body["panel"]["mdfCodes"]==["MDF-TR-001"]
    assert body["panel"]["metadata"]["version"]==3
    exported=client.get("/panels/CMP6000/export")
    assert exported.status_code==200
    assert exported.mimetype=="application/json"
    assert 'attachment; filename="CMP6000.json"' in exported.headers["Content-Disposition"]
    exported_body=json.loads(exported.data)
    assert exported_body["schemaVersion"]==3

def test_panel_import_requires_replace_for_existing_panel(client):
    create_panel(client)
    payload=client.get("/api/panels/CMP1000").get_json()
    payload["panel"]["panelName"]="Imported Replacement"
    blocked=client.post(
        "/panels/import",
        data={"panel_file":(io.BytesIO(json.dumps(payload).encode("utf-8")),"panel.json")},
        content_type="multipart/form-data",
    )
    assert blocked.status_code==400
    assert client.get("/api/panels/CMP1000").get_json()["panel"]["panelName"]=="Test Transformers"

    replaced=client.post(
        "/panels/import",
        data={
            "panel_file":(io.BytesIO(json.dumps(payload).encode("utf-8")),"panel.json"),
            "replace_existing":"1",
        },
        content_type="multipart/form-data",
    )
    assert replaced.status_code==302
    assert client.get("/api/panels/CMP1000").get_json()["panel"]["panelName"]=="Imported Replacement"

def test_panel_import_rejects_future_schema(client):
    payload={"schemaVersion":99,"panel":{}}
    response=client.post(
        "/panels/import",
        data={"panel_file":(io.BytesIO(json.dumps(payload).encode("utf-8")),"future.json")},
        content_type="multipart/form-data",
    )
    assert response.status_code==400
    assert b"Unsupported schemaVersion 99" in response.data


def test_seeded_demo_panels_use_historical_abb_europe_hub_data(tmp_path):
    seeded_app=create_app({
        "TESTING": True,
        "DATABASE": str(tmp_path / "seeded.sqlite"),
        "SEED_DEMO": True,
        "SECRET_KEY": "test",
    })
    seeded_client=seeded_app.test_client()

    portfolio=seeded_client.get("/")
    assert portfolio.status_code==200
    assert b"Power and Distribution Transformers" in portfolio.data
    assert b"LV &amp; MV Cables" in portfolio.data
    assert b"MV Switchgear" in portfolio.data
    assert b"Instrument Transformers" in portfolio.data
    assert b"Civil Works" in portfolio.data
    assert b"Engineering Services" in portfolio.data
    assert b"Protection &amp; Control Relays" in portfolio.data

    body=seeded_client.get("/api/panels/ABB-3GX").get_json()
    assert body["panel"]["region"]=={"level":"HUB","value":"Europe"}
    assert body["panel"]["metadata"]["legacySource"]=="Dynamic Supplier Panel 07Sep2021.xlsm"
    assert body["panel"]["metadata"]["legacySheet"]=="3GX"
    assert body["panel"]["leadMdfCode"]=="3GX"
    assert body["panel"]["suppliers"][0]["supplierName"]=="Koncar Power Transformers Ltd."
    assert body["panel"]["suppliers"][0]["address"]
    assert body["panel"]["suppliers"][0]["postCode"]
    assert body["panel"]["suppliers"][0]["customFields"]["country"]=="Croatia"
    assert body["panel"]["suppliers"][0]["customFields"]["classification"]=="2. HBU Preferred"
    assert body["panel"]["suppliers"][0]["customFields"]["ksm"]=="Emre Gul"
    assert body["panel"]["suppliers"][0]["customFields"]["supplier_risk"]=="Medium"

    civil=seeded_client.get("/api/panels/ABB-CIV").get_json()
    assert civil["panel"]["region"]=={"level":"HUB","value":"Europe"}
    field_ids={f["fieldId"] for f in civil["panel"]["supplierFields"]}
    assert {"branch_location","turnover_kusd","minimum_project_amount_kusd"} <= field_ids

    edit_page=seeded_client.get("/panels/ABB-3GX/edit")
    assert edit_page.status_code==200
    assert b"3GX" in edit_page.data
