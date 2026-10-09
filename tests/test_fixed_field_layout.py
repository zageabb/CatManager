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
