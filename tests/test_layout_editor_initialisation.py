from pathlib import Path


def test_layout_editor_initialises_on_page_load():
    js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text()
    assert "renderGroups();renderFields();renderLayout();sync();" in js
    assert "renderGroups();renderFields();sync();" not in js
    assert 'const layoutRoot=document.querySelector("#field-layout-editor")' in js


def test_configuration_exposes_layout_editor():
    html = (Path(__file__).resolve().parents[1] / "templates" / "panel_configuration.html").read_text()
    assert 'id="field-layout-editor"' in html
    assert 'name="field_layout_json"' in html


def test_fixed_group_change_updates_current_layout_entry():
    js = (Path(__file__).resolve().parents[1] / "static" / "app.js").read_text()
    assert 'const current=fieldLayout.find(entry=>entry.ref===item.ref)' in js
    assert 'if(current)current.groupId=e.target.value' in js
    assert 'item.groupId=e.target.value;const field=fields.find' not in js


def test_field_placement_uses_dedicated_responsive_grid():
    root = Path(__file__).resolve().parents[1]
    js = (root / "static" / "app.js").read_text()
    css = (root / "static" / "app.css").read_text()
    assert 'row.className="field-row layout-field-row"' in js
    assert '#field-layout-editor .layout-field-row' in css
    assert 'grid-template-columns:minmax(240px, 1fr) 72px minmax(165px, 220px) 36px 36px' in css
    assert 'width:36px;' in css
    assert '@media(max-width:720px)' in css
