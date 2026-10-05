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
        "mdf_code": "MDF-TR-001",
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
    assert b"CMP1000" not in client.get("/").data
    assert b"CMP1000" in client.get("/?archived=1").data
    body=client.get("/api/panels/CMP1000").get_json()
    assert body["panel"]["metadata"]["status"]=="archived"
    assert body["panel"]["metadata"]["auditTrail"][-1]["action"]=="panel_archived"

    restored=client.post("/panels/CMP1000/restore")
    assert restored.status_code==302
    assert b"CMP1000" in client.get("/").data
    body=client.get("/api/panels/CMP1000").get_json()
    assert body["panel"]["metadata"]["status"]=="active"
    assert body["panel"]["metadata"]["auditTrail"][-1]["action"]=="panel_restored"
