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
