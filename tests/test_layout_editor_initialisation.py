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
