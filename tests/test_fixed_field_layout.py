import pytest

from app import default_field_layout, normalise_field_layout


def test_legacy_layout_keeps_fixed_fields_first():
    fields = [{"fieldId": "quality", "groupId": "assessment"}]
    layout = default_field_layout(fields)
    assert [x["ref"] for x in layout] == [
        "fixed:supplierId", "fixed:supplierName", "fixed:address",
        "fixed:postCode", "custom:quality"
    ]
    assert layout[-1]["groupId"] == "assessment"


def test_fixed_and_custom_fields_move_into_same_group():
    fields = [{"fieldId": "quality", "groupId": ""}]
    groups = [{"groupId": "identity", "name": "Identification"}]
    layout = [
        {"ref": "custom:quality", "groupId": "identity"},
        {"ref": "fixed:supplierName", "groupId": "identity"},
        {"ref": "fixed:supplierId", "groupId": "identity"},
        {"ref": "fixed:address", "groupId": ""},
        {"ref": "fixed:postCode", "groupId": ""},
    ]
    assert normalise_field_layout(layout, fields, groups) == layout


@pytest.mark.parametrize("layout", [
    [{"ref": "fixed:supplierId", "groupId": ""}],
    [{"ref": "fixed:supplierId", "groupId": ""}] * 4,
    [{"ref": "fixed:unknown", "groupId": ""}] * 4,
    [{"ref": "fixed:supplierId", "groupId": "missing"}] * 4,
])
def test_invalid_layout_rejected(layout):
    with pytest.raises(ValueError):
        normalise_field_layout(layout, [], [])


def test_fixed_field_group_persists_in_supplier_and_bulk_forms(tmp_path):
    import json
    from app import create_app

    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "layout.sqlite"),
                      "SEED_DEMO": False, "SECRET_KEY": "test"})
    client = app.test_client()
    created = client.post("/panels/new", data={
        "panel_id": "LAYOUT-001", "panel_name": "Layout Panel",
        "category": "Transformers", "business": "GI",
        "region_level": "Country", "region_value": "United Kingdom",
        "owner": "Test", "mdf_codes": ["MDF-TR-001"],
        "lead_mdf_code": "MDF-TR-001",
        "fields_json": json.dumps([{"fieldId":"quality", "fieldName":"Quality",
                                    "type":"text", "groupId":""}]),
    })
    assert created.status_code == 302
    groups = [{"groupId":"identity", "name":"Identity", "order":1},
              {"groupId":"other", "name":"Other", "order":2}]
    layout = [{"ref":"fixed:supplierName", "groupId":"identity"},
              {"ref":"custom:quality", "groupId":"identity"},
              {"ref":"fixed:supplierId", "groupId":"identity"},
              {"ref":"fixed:address", "groupId":"other"},
              {"ref":"fixed:postCode", "groupId":""}]
    response = client.post("/panels/LAYOUT-001/configuration", data={
        "field_groups_json": json.dumps(groups),
        "fields_json": json.dumps([{"fieldId":"quality", "fieldName":"Quality",
                                    "type":"text", "groupId":"identity"}]),
        "field_layout_json": json.dumps(layout),
    })
    assert response.status_code == 302
    saved = client.get("/api/panels/LAYOUT-001").get_json()
    assert saved["panel"]["fieldLayout"] == layout
    for url in ("/panels/LAYOUT-001/suppliers/new",
                "/panels/LAYOUT-001/suppliers/bulk-edit"):
        page = client.get(url)
        assert page.status_code == 200
        html = page.get_data(as_text=True)
        identity = html.index("Identity")
        other = html.index("Other", identity)
        assert identity < html.index("Supplier Name", identity) < other
        assert identity < html.index("Quality", identity) < other
        assert identity < html.index("Supplier ID", identity) < other
        assert other < html.index("Address", other)
