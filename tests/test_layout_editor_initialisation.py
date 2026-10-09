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


def test_configuration_section_navigation_preserves_single_form():
    root = Path(__file__).resolve().parents[1]
    html = (root / "templates" / "panel_configuration.html").read_text()
    css = (root / "static" / "app.css").read_text()
    assert 'aria-label="Configuration sections"' in html
    for section in ("fields", "widgets", "scoring"):
        assert 'href="#configuration_' + section + '"' in html
        assert 'id="configuration_' + section + '"' in html
    assert html.count('id="panel-form"') == 1
    assert 'data-unsaved-guard' in html
    for name in ("field_layout_json", "fields_json", "field_groups_json",
                 "dashboard_widgets_json", "scoring_criteria_json"):
        assert 'name="' + name + '"' in html
    assert 'id="configuration-widgets"' in html
    assert 'data-csrf-token=' in html
    assert '@media(max-width:850px)' in css


def test_configuration_focused_panes_preserve_all_save_fields():
    root = Path(__file__).resolve().parents[1]
    html = (root / "templates" / "panel_configuration.html").read_text()
    js = (root / "static" / "app.js").read_text()
    for section in ("fields", "widgets", "scoring"):
        assert 'class="configuration-pane" id="configuration-' + section + '"' in html
        assert 'href="#configuration-' + section + '"' in html
    assert 'data-config-navigation' in html
    assert html.count('id="panel-form"') == 1
    assert 'name="field_layout_json"' in html
    assert 'name="dashboard_widgets_json"' in html
    assert 'name="scoring_criteria_json"' in html
    assert 'pane.hidden=pane.id!==active' in js
    assert 'window.addEventListener("hashchange"' in js
    assert 'addEventListener("invalid"' in js


def test_configuration_related_tools_are_outside_post_form():
    html = (Path(__file__).resolve().parents[1] / "templates" / "panel_configuration.html").read_text()
    assert html.index("</form>") < html.index('class="configuration-related-tools"')
    for endpoint in ("panel_edit", "panel_template_list", "supplier_master_sync_preview",
                     "panel_export", "panel_audit"):
        assert "url_for('" + endpoint + "'" in html
    assert "Save your configuration changes before leaving this page." in html


def test_related_tool_routes_render_for_existing_panel(tmp_path):
    from app import create_app
    import json
    app = create_app({"TESTING": True, "DATABASE": str(tmp_path / "related.sqlite"),
                      "SEED_DEMO": False, "SECRET_KEY": "test"})
    client = app.test_client()
    response = client.post("/panels/new", data={
        "panel_id":"TOOLS-001","panel_name":"Tools Panel","category":"Transformers",
        "business":"GI","region_level":"Country","region_value":"United Kingdom",
        "owner":"Test","mdf_codes":["MDF-TR-001"],"lead_mdf_code":"MDF-TR-001",
        "fields_json":json.dumps([])
    })
    assert response.status_code == 302
    html = client.get("/panels/TOOLS-001/configuration").get_data(as_text=True)
    assert "/panels/TOOLS-001/edit" in html
    assert "/panel-templates" in html
    assert "/panels/TOOLS-001/suppliers/master-sync" in html
    assert "/panels/TOOLS-001/export" in html
    assert "/panels/TOOLS-001/audit" in html
