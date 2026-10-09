(() => {
  const root = document.querySelector("#custom-fields");
  const hidden = document.querySelector("#fields-json");
  const add = document.querySelector("#add-field");
  const groupRoot = document.querySelector("#field-groups");
  const groupHidden = document.querySelector("#field-groups-json");
  const addGroup = document.querySelector("#add-group");

  function esc(v){return String(v).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c];});}
  function slug(v){return v.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"") || "custom_field";}
  function parseValue(el){if(!el)return [];try{return JSON.parse(el.value||"[]");}catch(e){return [];}}
  let fields=parseValue(hidden);
  let groups=parseValue(groupHidden);
  const templateSelector=document.querySelector("#template-selector");
  const addTemplateField=document.querySelector("#add-template-field");
  let fieldTemplates=[];
  function nextFieldId(name){
    const base=slug(name);let id=base,n=2;
    const ids=new Set(fields.map(function(f){return f.fieldId;}));
    while(ids.has(id)){id=base+"_"+n;n+=1;}
    return id;
  }
  async function loadFieldTemplates(){
    if(!templateSelector)return;
    try{
      const response=await fetch("/api/field-templates");
      if(!response.ok)throw new Error("Unable to load templates");
      fieldTemplates=await response.json();
      templateSelector.innerHTML='<option value="">Select predefined field…</option>'+
        fieldTemplates.map(function(t){return '<option value="'+esc(t.templateId)+'">'+esc(t.fieldName)+' ('+esc(t.type)+')</option>';}).join("");
    }catch(e){templateSelector.innerHTML='<option value="">Field library unavailable</option>';}
  }
  if(addTemplateField)addTemplateField.addEventListener("click",function(){
    const t=fieldTemplates.find(function(x){return x.templateId===templateSelector.value;});
    if(!t)return;
    fields.push({fieldId:nextFieldId(t.fieldName),fieldName:t.fieldName,type:t.type,
      options:(t.options||[]).slice(),required:!!t.required,groupId:""});
    renderFields();renderLayout();sync();
  });
  loadFieldTemplates();


  const layoutRoot=document.querySelector("#field-layout-editor");
  const layoutHidden=document.querySelector("#field-layout-json");
  const fixedLabels={supplierId:"Supplier ID / BPID",supplierName:"Supplier Name",address:"Address",postCode:"Post Code"};
  let fieldLayout=parseValue(layoutHidden);
  function reconcileLayout(){
    const valid=["supplierId","supplierName","address","postCode"].map(k=>"fixed:"+k).concat(fields.map(f=>"custom:"+f.fieldId));
    const previous=new Set(),clean=[];
    fieldLayout.forEach(item=>{
      if(valid.includes(item.ref) && !previous.has(item.ref)){
        clean.push({ref:item.ref,groupId:groups.some(g=>g.groupId===item.groupId)?item.groupId:""});
        previous.add(item.ref);
      }
    });
    valid.forEach(ref=>{if(!previous.has(ref)){
      const f=fields.find(f=>"custom:"+f.fieldId===ref);
      clean.push({ref,groupId:f?.groupId||""});
    }});
    fieldLayout=clean;
  }
  function renderLayout(){
    if(!layoutRoot)return;
    reconcileLayout();layoutRoot.innerHTML="";
    fieldLayout.forEach((item,index)=>{
      const field=fields.find(f=>"custom:"+f.fieldId===item.ref);
      const label=item.ref.startsWith("fixed:")?fixedLabels[item.ref.slice(6)]:(field?.fieldName||item.ref);
      const row=document.createElement("div");
      row.className="field-row";
      row.innerHTML='<strong>'+esc(label)+'</strong><span class="field-type">'+(item.ref.startsWith("fixed:")?"Fixed":"Custom")+'</span>'+
        '<select class="layout-group" aria-label="Group for '+esc(label)+'">'+groupOptions(item.groupId)+'</select>'+
        '<button type="button" class="btn compact layout-up" aria-label="Move '+esc(label)+' up" '+(index===0?"disabled":"")+'>↑</button>'+
        '<button type="button" class="btn compact layout-down" aria-label="Move '+esc(label)+' down" '+(index===fieldLayout.length-1?"disabled":"")+'>↓</button>';
      row.querySelector(".layout-group").addEventListener("change",e=>{const current=fieldLayout.find(entry=>entry.ref===item.ref);if(current)current.groupId=e.target.value;const field=fields.find(f=>"custom:"+f.fieldId===item.ref);if(field){field.groupId=e.target.value;renderFields();}sync();});
      row.querySelector(".layout-up").addEventListener("click",()=>{[fieldLayout[index-1],fieldLayout[index]]=[fieldLayout[index],fieldLayout[index-1]];renderLayout();sync();});
      row.querySelector(".layout-down").addEventListener("click",()=>{[fieldLayout[index],fieldLayout[index+1]]=[fieldLayout[index+1],fieldLayout[index]];renderLayout();sync();});
      layoutRoot.appendChild(row);
    });
  }
  function sync(){
    if(layoutHidden){reconcileLayout();layoutHidden.value=JSON.stringify(fieldLayout);}
    if(hidden)hidden.value=JSON.stringify(fields.map(function(f,i){f.order=i+1;return f;}));
    if(groupHidden)groupHidden.value=JSON.stringify(groups.map(function(g,i){g.order=i+1;return g;}));
  }
  function groupOptions(current){
    return '<option value="">Ungrouped</option>'+groups.map(function(g){
      return '<option value="'+esc(g.groupId)+'" '+(current===g.groupId?"selected":"")+'>'+esc(g.name||"Untitled group")+'</option>';
    }).join("");
  }
  function renderGroups(){
    if(!groupRoot)return;
    groupRoot.innerHTML="";
    groups.forEach(function(g,index){
      const row=document.createElement("div");
      row.className="field-group-row";
      row.innerHTML=
        '<span class="group-order">'+(index+1)+'</span>'+
        '<input class="group-name" value="'+esc(g.name||"")+'" placeholder="Group name">'+
        '<div class="group-row-actions">'+
        '<button type="button" class="btn compact group-up" '+(index===0?"disabled":"")+'>↑</button>'+
        '<button type="button" class="btn compact group-down" '+(index===groups.length-1?"disabled":"")+'>↓</button>'+
        '<button type="button" class="btn compact danger group-delete">Delete</button></div>';
      row.querySelector(".group-name").addEventListener("input",function(e){groups[index].name=e.target.value;renderFields();renderLayout();sync();});
      row.querySelector(".group-up").addEventListener("click",function(){if(index<1)return;const moved=groups.splice(index,1)[0];groups.splice(index-1,0,moved);renderGroups();renderFields();renderLayout();sync();});
      row.querySelector(".group-down").addEventListener("click",function(){if(index>=groups.length-1)return;const moved=groups.splice(index,1)[0];groups.splice(index+1,0,moved);renderGroups();renderFields();renderLayout();sync();});
      row.querySelector(".group-delete").addEventListener("click",function(){
        const gid=g.groupId;
        fields.forEach(function(field){if(field.groupId===gid)field.groupId="";});
        fieldLayout.forEach(item=>{if(item.groupId===gid)item.groupId="";});
        groups.splice(index,1);
        renderGroups();renderFields();renderLayout();sync();
      });
      groupRoot.appendChild(row);
    });
    if(!groups.length){
      const empty=document.createElement("p");
      empty.className="help-text";
      empty.textContent="No groups defined. Existing and new custom fields can remain in the Ungrouped section.";
      groupRoot.appendChild(empty);
    }
  }
  function renderFields(){
    if(!root)return;
    root.innerHTML="";
    fields.forEach(function(f,index){
      const row=document.createElement("div");
      row.className="field-row custom";
      row.draggable=true;
      row.dataset.index=index;
      const opts=["text","number","dropdown","date","boolean","stars","multiselect_blocks"].map(function(x){return '<option value="'+x+'" '+(f.type===x?"selected":"")+'>'+x.charAt(0).toUpperCase()+x.slice(1)+'</option>';}).join("");
      row.innerHTML=
        '<span class="drag" title="Drag to reorder">☰</span>'+
        '<input class="field-name" value="'+esc(f.fieldName||"")+'" placeholder="Field name">'+
        '<select class="field-kind">'+opts+'</select>'+
        '<select class="field-group" aria-label="Field group">'+groupOptions(f.groupId||"")+'</select>'+
        '<input class="field-options '+(["dropdown","multiselect_blocks"].includes(f.type)?"":"hidden")+'" value="'+esc((f.options||[]).join(", "))+'" placeholder="Options, comma separated">'+
        '<label class="required-toggle"><input type="checkbox" '+(f.required?"checked":"")+'> Required</label>'+
        '<button type="button" class="btn compact save-template" title="Add to predefined library">Save to library</button>'+
        '<button type="button" class="icon-delete" aria-label="Delete">×</button>';
      row.querySelector(".field-name").addEventListener("input",function(e){
        fields[index].fieldName=e.target.value;
        if(!fields[index].fieldId || fields[index]._generated){fields[index].fieldId=slug(e.target.value);fields[index]._generated=true;}
        sync();
      });
      row.querySelector(".field-kind").addEventListener("change",function(e){
        fields[index].type=e.target.value;
        if(!["dropdown","multiselect_blocks"].includes(e.target.value))fields[index].options=[];
        renderFields();sync();
      });
      row.querySelector(".field-group").addEventListener("change",function(e){fields[index].groupId=e.target.value;const item=fieldLayout.find(item=>item.ref==="custom:"+fields[index].fieldId);if(item)item.groupId=e.target.value;renderLayout();sync();});
      row.querySelector(".field-options").addEventListener("input",function(e){fields[index].options=e.target.value.split(",").map(function(x){return x.trim();}).filter(Boolean);sync();});
      row.querySelector(".required-toggle input").addEventListener("change",function(e){fields[index].required=e.target.checked;sync();});
      row.querySelector(".save-template").addEventListener("click",async function(){
        const button=this;
        button.disabled=true;
        try {
          const response=await fetch("/api/field-templates",{
            method:"POST",headers:{"Content-Type":"application/json"},
            body:JSON.stringify(fields[index])
          });
          if(!response.ok){const error=await response.json();throw new Error(error.error||"Save failed");}
          await loadFieldTemplates();
          button.textContent="Saved";
        }catch(error){button.textContent=error.message||"Save failed";button.disabled=false;}
      });
      row.querySelector(".icon-delete").addEventListener("click",function(){fields.splice(index,1);renderFields();renderLayout();sync();});
      row.addEventListener("dragstart",function(e){e.dataTransfer.setData("text/plain",String(index));});
      row.addEventListener("dragover",function(e){e.preventDefault();});
      row.addEventListener("drop",function(e){e.preventDefault();const from=Number(e.dataTransfer.getData("text/plain"));const moved=fields.splice(from,1)[0];fields.splice(index,0,moved);renderFields();sync();});
      root.appendChild(row);
    });
  }
  if(add)add.addEventListener("click",function(){fields.push({fieldId:"custom_field_"+(fields.length+1),fieldName:"",type:"text",options:[],required:false,groupId:"",_generated:true});renderFields();sync();});
  if(addGroup)addGroup.addEventListener("click",function(){
    let n=groups.length+1, gid="group_"+n;
    const used=new Set(groups.map(function(g){return g.groupId;}));
    while(used.has(gid)){n+=1;gid="group_"+n;}
    groups.push({groupId:gid,name:"New group",order:groups.length+1});
    renderGroups();renderFields();renderLayout();sync();
  });
  renderGroups();renderFields();renderLayout();sync();


  const widgetRoot=document.querySelector("#dashboard-widgets");
  const widgetHidden=document.querySelector("#dashboard-widgets-json");
  const addWidget=document.querySelector("#add-widget");
  let widgets=parseValue(widgetHidden);
  const widgetMetrics=["count","count_where","sum","average","minimum","maximum","distinct","ratio","percentage"];
  const availableWidgetFields=[{fieldId:"supplierId",fieldName:"Supplier ID",type:"text"},
    {fieldId:"supplierName",fieldName:"Supplier Name",type:"text"}]
    .concat(widgetRoot ? JSON.parse(widgetRoot.dataset.fields||"[]") : []);
  function fieldSelect(current,ratingOnly){
    const candidates=ratingOnly?availableWidgetFields.filter(f=>["stars","number"].includes(f.type)):availableWidgetFields;
    return '<option value="">Choose source field…</option>'+candidates.map(function(f){
      return '<option value="'+esc(f.fieldId)+'" '+(f.fieldId===current?"selected":"")+'>'+esc(f.fieldName)+' ('+esc(f.type||"text")+')</option>';
    }).join("");
  }
  let previewRequest=0;
  function scheduleWidgetPreview(){
    if(!widgetRoot)return;
    const requestId=++previewRequest;
    const valid=widgets.every(w=>w.title && (w.metric==="count" || w.fieldId) &&
      (!["ratio","percentage"].includes(w.metric) || w.otherFieldId));
    widgetRoot.querySelectorAll(".widget-preview").forEach(el=>{
      el.textContent=valid?"Calculating from current supplier data…":"Choose all required fields to preview";
    });
    if(!valid)return;
    fetch(widgetRoot.dataset.previewUrl,{
      method:"POST",headers:{"Content-Type":"application/json","X-CSRF-Token":widgetRoot.dataset.csrfToken||""},
      body:JSON.stringify({widgets:widgets})
    }).then(async response=>{
      const contentType=response.headers.get("content-type")||"";
      if(!contentType.includes("application/json"))throw new Error("KPI preview request failed (HTTP "+response.status+"). Refresh the page and try again.");
      const data=await response.json();
      if(requestId!==previewRequest)return;
      if(!response.ok)throw new Error(data.error||"Unable to preview");
      const displayed=data.widgets||[];
      widgets.forEach((w,i)=>{
        const el=widgetRoot.querySelectorAll(".widget-preview")[i];
        if(!el)return;
        const match=displayed.find(p=>p.title===w.title);
        if(!match){el.textContent=w.display==="supplier"?"Supplier-level only — preview in supplier table":"No panel preview";return;}
        if(match.value===null){el.textContent="No available data yet";return;}
        const value=Number(match.value);
        let shown=Number.isFinite(value)?value.toLocaleString(undefined,{maximumFractionDigits:2}):"—";
        if(w.format==="percentage"||w.metric==="percentage")shown+="%";
        if(w.format==="currency")shown=(match.currencyPrefix||"")+shown;
        if(["stars","stars_both"].includes(w.format)){
          const rating=Math.max(0,Math.min(5,value));
          shown="★".repeat(Math.floor(rating))+"☆".repeat(5-Math.floor(rating))+
            (w.format==="stars_both"?" "+shown+"/5":"");
        }
        el.textContent=shown+" · "+(match.excluded||0)+" excluded";
      });
    }).catch(err=>{
      if(requestId!==previewRequest)return;
      widgetRoot.querySelectorAll(".widget-preview").forEach(el=>el.textContent=err.message);
    });
  }
  function renderWidgets(){
    if(!widgetRoot)return;
    widgetRoot.innerHTML="";
    widgets.forEach(function(w,i){
      const row=document.createElement("div");
      row.className="field-row custom widget-row";
      row.innerHTML='<input class="widget-title" aria-label="Widget title" placeholder="KPI title" value="'+esc(w.title||"")+'">'+
        '<select class="widget-metric" aria-label="Calculation">'+widgetMetrics.map(function(m){return '<option value="'+m+'" '+(w.metric===m?"selected":"")+'>'+m.replace("_"," ")+'</option>';}).join("")+'</select>'+
        '<select class="widget-field" aria-label="Source custom field">'+fieldSelect(w.fieldId||"",["stars","stars_both"].includes(w.format))+'</select>'+
        '<select class="widget-other" aria-label="Denominator field">'+fieldSelect(w.otherFieldId||"")+'</select>'+
        '<input class="widget-match" aria-label="Count matching value" placeholder="Equals..." value="'+esc(w.match||"")+'">'+
        '<select class="widget-format" aria-label="Output format">'+["number","currency","percentage","stars","stars_both"].map(function(f){return '<option value="'+f+'" '+(w.format===f?"selected":"")+'>'+({stars:"Stars",stars_both:"Stars and number",number:"Number",currency:"Currency",percentage:"Percentage"}[f])+'</option>';}).join("")+'</select>'+
        '<select class="widget-display" aria-label="Display location">'+["panel","supplier","both"].map(function(d){return '<option value="'+d+'" '+((w.display||"panel")===d?"selected":"")+'>'+({panel:"Panel KPI",supplier:"Supplier column",both:"Both"}[d])+'</option>';}).join("")+'</select>'+
        '<button class="btn compact danger widget-remove" type="button">Remove</button>'+        '<div class="widget-preview" role="status" aria-live="polite">Calculating preview…</div>';
      [[".widget-title","title"],[".widget-metric","metric"],[".widget-field","fieldId"],
       [".widget-other","otherFieldId"],[".widget-match","match"],[".widget-format","format"],[".widget-display","display"]].forEach(function(item){
        row.querySelector(item[0]).addEventListener("change",function(e){w[item[1]]=e.target.value;if(item[1]==="format" && ["stars","stars_both"].includes(w.format)){if(!["stars","number"].includes((availableWidgetFields.find(f=>f.fieldId===w.fieldId)||{}).type))w.fieldId="";if(!["average","minimum","maximum"].includes(w.metric))w.metric="average";}syncWidgets();renderWidgets();});
      });
      row.querySelector(".widget-title").addEventListener("input",function(e){w.title=e.target.value;syncWidgets();scheduleWidgetPreview();});
      row.querySelector(".widget-match").addEventListener("input",function(e){w.match=e.target.value;syncWidgets();scheduleWidgetPreview();});
      row.querySelector(".widget-metric").querySelectorAll("option").forEach(function(opt){opt.disabled=["stars","stars_both"].includes(w.format)&&!["average","minimum","maximum"].includes(opt.value);});
      row.querySelector(".widget-other").hidden=!["ratio","percentage"].includes(w.metric);
      row.querySelector(".widget-match").hidden=w.metric!=="count_where";
      row.querySelector(".widget-field").hidden=w.metric==="count";
      row.querySelector(".widget-remove").addEventListener("click",function(){widgets.splice(i,1);renderWidgets();syncWidgets();});
      widgetRoot.appendChild(row);
    });
    if(addWidget)addWidget.disabled=widgets.length>=6;
    scheduleWidgetPreview();
  }
  function syncWidgets(){if(widgetHidden)widgetHidden.value=JSON.stringify(widgets);}
  if(addWidget)addWidget.addEventListener("click",function(){
    if(widgets.length>=6)return;
    widgets.push({widgetId:"widget_"+Date.now()+"_"+widgets.length,title:"New KPI",metric:"count",
      fieldId:"",otherFieldId:"",match:"",format:"number",display:"panel"});
    syncWidgets();renderWidgets();
  });
  renderWidgets();

  const mdfPicker=document.querySelector("[data-mdf-multiselect]");
  if(mdfPicker){
    const trigger=mdfPicker.querySelector(".mdf-select-trigger");
    const menu=mdfPicker.querySelector(".mdf-select-menu");
    const search=mdfPicker.querySelector(".mdf-search");
    const clear=mdfPicker.querySelector(".mdf-clear");
    const options=Array.from(mdfPicker.querySelectorAll(".mdf-option"));
    const checks=Array.from(mdfPicker.querySelectorAll('input[name="mdf_codes"]'));
    const chips=mdfPicker.querySelector(".mdf-selected-chips");
    const triggerText=mdfPicker.querySelector(".mdf-trigger-text");
    const count=mdfPicker.querySelector(".mdf-trigger-count");
    const lead=document.querySelector("#lead-mdf-select");
    const currentLead=lead ? lead.dataset.current : "";

    function selected(){
      return checks.filter(function(c){return c.checked;});
    }
    function refreshLead(){
      if(!lead)return;
      const previous=lead.value || currentLead;
      lead.innerHTML='<option value="">Select lead MDF…</option>';
      selected().forEach(function(c){
        const opt=document.createElement("option");
        opt.value=c.value;
        opt.textContent=c.value+" — "+(c.dataset.description||"");
        if(c.value===previous)opt.selected=true;
        lead.appendChild(opt);
      });
      if(previous && !selected().some(function(c){return c.value===previous;}))lead.value="";
    }
    function refresh(){
      const picked=selected();
      triggerText.textContent=picked.length ? picked.slice(0,2).map(function(c){return c.value;}).join(", ")+(picked.length>2?"…":"") : "Select MDF codes…";
      count.textContent=picked.length ? String(picked.length)+" selected" : "";
      chips.innerHTML="";
      picked.forEach(function(c){
        const chip=document.createElement("button");
        chip.type="button";
        chip.className="mdf-chip";
        chip.innerHTML="<strong>"+esc(c.value)+"</strong><span>×</span>";
        chip.title="Remove "+c.value;
        chip.addEventListener("click",function(){c.checked=false;refresh();});
        chips.appendChild(chip);
      });
      refreshLead();
    }
    function setOpen(open){
      menu.hidden=!open;
      trigger.setAttribute("aria-expanded",open?"true":"false");
      if(open){search.focus();search.select();}
    }
    trigger.addEventListener("click",function(e){e.stopPropagation();setOpen(menu.hidden);});
    menu.addEventListener("click",function(e){e.stopPropagation();});
    document.addEventListener("click",function(){if(!menu.hidden)setOpen(false);});
    search.addEventListener("input",function(){
      const q=search.value.trim().toLowerCase();
      options.forEach(function(row){row.hidden=q && !row.dataset.search.includes(q);});
    });
    clear.addEventListener("click",function(){checks.forEach(function(c){c.checked=false;});refresh();});
    checks.forEach(function(c){c.addEventListener("change",refresh);});
    refresh();
  }

  const supplierPicker=document.querySelector("[data-supplier-master-picker]");
  if(supplierPicker){
    const search=supplierPicker.querySelector(".supplier-master-search");
    const results=supplierPicker.querySelector(".supplier-master-results");
    const form=supplierPicker.closest("form");
    const idInput=form.querySelector('[name="supplier_id"]');
    const nameInput=form.querySelector('[name="supplier_name"]');
    const addressInput=form.querySelector('[name="address"]');
    const postInput=form.querySelector('[name="post_code"]');
    let timer=null;
    let controller=null;

    function hideResults(){results.hidden=true;results.innerHTML="";}
    function chooseSupplier(item){
      idInput.value=item.bpid||"";
      nameInput.value=item.supplier_name||"";
      addressInput.value=item.address||"";
      postInput.value=item.post_code||"";
      search.value=(item.bpid||"")+" — "+(item.supplier_name||"");
      hideResults();
      nameInput.focus();
    }
    function renderSupplierResults(items){
      results.innerHTML="";
      if(!items.length){
        const empty=document.createElement("div");
        empty.className="supplier-result-empty";
        empty.textContent="No active master suppliers found.";
        results.appendChild(empty);
        results.hidden=false;
        return;
      }
      items.forEach(function(item){
        const btn=document.createElement("button");
        btn.type="button";
        btn.className="supplier-result";
        btn.innerHTML='<strong>'+esc(item.bpid)+'</strong><span>'+esc(item.supplier_name)+'</span><small>'+esc(item.address||"")+'</small>';
        btn.addEventListener("click",function(){chooseSupplier(item);});
        results.appendChild(btn);
      });
      results.hidden=false;
    }
    async function runSupplierSearch(){
      const q=search.value.trim();
      if(q.length<2){hideResults();return;}
      if(controller)controller.abort();
      controller=new AbortController();
      try{
        const response=await fetch("/api/supplier-master/search?q="+encodeURIComponent(q),{signal:controller.signal});
        if(!response.ok)throw new Error("search failed");
        renderSupplierResults(await response.json());
      }catch(e){
        if(e.name!=="AbortError")hideResults();
      }
    }
    search.addEventListener("input",function(){
      clearTimeout(timer);
      timer=setTimeout(runSupplierSearch,180);
    });
    search.addEventListener("keydown",function(e){
      if(e.key==="Escape")hideResults();
    });
    document.addEventListener("click",function(e){
      if(!supplierPicker.contains(e.target))hideResults();
    });
  }


  // DEV-032: client-side filtering and stable typed sorting of supplier rows.
  const supplierTable=document.querySelector("[data-supplier-table]");
  const supplierControls=document.querySelector("[data-supplier-controls]");
  if(supplierTable && supplierControls){
    const body=supplierTable.tBodies[0];
    const rows=Array.from(body.querySelectorAll(".supplier-data-row"));
    const query=supplierControls.querySelector(".supplier-table-search");
    const filterField=supplierControls.querySelector(".supplier-filter-field");
    const sortField=supplierControls.querySelector(".supplier-sort-field");
    const direction=supplierControls.querySelector(".supplier-sort-direction");
    const resultCount=supplierControls.querySelector(".supplier-results-count");
    const noMatches=document.querySelector(".supplier-no-matches");
    const normalise=v=>String(v==null?"":v).toLocaleLowerCase().trim();

    const columnSettings=document.querySelector("[data-supplier-column-settings]");
    const header=supplierTable.tHead.rows[0];
    const headings=Array.from(header.cells);
    const rowCells=new Map(rows.map(row=>[row,Array.from(row.cells)]));
    const fixed=new Set([0,1,2,headings.length-1]);
    const storageKey="catmanager:columns:"+supplierTable.dataset.panelId;
    const initial=Array.from({length:headings.length},(_,i)=>i);
    let columnOrder=initial.slice();
    let hiddenColumns=new Set();
    const originalCell=(row,i)=>rowCells.get(row)?.[i];
    function restoreColumnPreferences(){
      try{
        const saved=JSON.parse(localStorage.getItem(storageKey)||"null");
        if(!saved||!Array.isArray(saved.order))return;
        const order=saved.order.filter(i=>Number.isInteger(i)&&i>=0&&i<headings.length);
        if(order.length!==headings.length||new Set(order).size!==headings.length)return;
        columnOrder=[0,1,2,...order.filter(i=>!fixed.has(i)),headings.length-1];
        hiddenColumns=new Set((saved.hidden||[]).filter(i=>!fixed.has(i)&&Number.isInteger(i)&&i>=0&&i<headings.length));
      }catch(_err){ /* Browser storage can be unavailable; defaults remain usable. */ }
    }
    function saveColumnPreferences(){
      try{localStorage.setItem(storageKey,JSON.stringify({order:columnOrder,hidden:[...hiddenColumns]}));}
      catch(_err){ /* Continue with this session's view when storage is unavailable. */ }
    }
    function renderColumns(){
      columnOrder.forEach(i=>header.appendChild(headings[i]));
      rows.forEach(row=>columnOrder.forEach(i=>row.appendChild(originalCell(row,i))));
      headings.forEach((cell,i)=>{cell.hidden=hiddenColumns.has(i);});
      rows.forEach(row=>rowCells.get(row).forEach((cell,i)=>{cell.hidden=hiddenColumns.has(i);}));
      const holder=columnSettings?.querySelector(".supplier-column-options");
      if(!holder)return;
      holder.replaceChildren();
      columnOrder.filter(i=>!fixed.has(i)).forEach(i=>{
        const item=document.createElement("div");
        item.className="supplier-column-option";
        const toggle=document.createElement("input");
        toggle.type="checkbox";toggle.checked=!hiddenColumns.has(i);
        toggle.setAttribute("aria-label","Show "+headings[i].textContent.trim());
        toggle.addEventListener("change",()=>{
          if(toggle.checked)hiddenColumns.delete(i);else hiddenColumns.add(i);
          saveColumnPreferences();renderColumns();
        });
        const name=document.createElement("span");
        name.textContent=headings[i].textContent.trim();
        const up=document.createElement("button"),down=document.createElement("button");
        for(const [button,label,delta] of [[up,"Move up",-1],[down,"Move down",1]]){
          button.type="button";button.className="btn compact";button.textContent=delta<0?"↑":"↓";
          button.setAttribute("aria-label",label+" "+name.textContent);
          const movable=columnOrder.filter(k=>!fixed.has(k));
          button.disabled=movable.indexOf(i)+(delta)<0||movable.indexOf(i)+(delta)>=movable.length;
          button.addEventListener("click",()=>{
            const ix=columnOrder.indexOf(i),swap=columnOrder.indexOf(movable[movable.indexOf(i)+delta]);
            [columnOrder[ix],columnOrder[swap]]=[columnOrder[swap],columnOrder[ix]];
            saveColumnPreferences();renderColumns();applySupplierView();
          });
        }
        item.append(toggle,name,up,down);holder.appendChild(item);
      });
    }
    if(columnSettings){
      columnSettings.querySelector(".supplier-column-reset").addEventListener("click",()=>{
        columnOrder=initial.slice();hiddenColumns.clear();saveColumnPreferences();renderColumns();applySupplierView();
      });
      restoreColumnPreferences();renderColumns();
    }

    function applySupplierView(){
      const needle=normalise(query.value);
      const filterIndex=filterField.value==="all"?null:Number(filterField.value);
      const sortIndex=Number(sortField.value);
      const sign=direction.value==="desc"?-1:1;
      const collator=new Intl.Collator(undefined,{numeric:true,sensitivity:"base"});
      const visible=rows.filter(row=>{
        const cells=rowCells.get(row).slice(1,-1);
        const candidates=filterIndex===null?cells:[originalCell(row,filterIndex)];
        const match=candidates.some(cell=>cell&&normalise(cell.dataset.filter??cell.textContent).includes(needle));
        row.hidden=!match;
        return match;
      });
      visible.sort((a,b)=>{
        const ca=originalCell(a,sortIndex),cb=originalCell(b,sortIndex);
        if(!ca||!cb)return 0;
        const av=ca.dataset.sort||ca.dataset.filter||"";
        const bv=cb.dataset.sort||cb.dataset.filter||"";
        if(!av&&!bv)return 0;
        if(!av)return 1;
        if(!bv)return -1;
        if(ca.dataset.type==="number"){
          const na=Number(av),nb=Number(bv);
          if(Number.isFinite(na)&&Number.isFinite(nb))return (na-nb)*sign;
        }
        return collator.compare(av,bv)*sign;
      });
      visible.forEach(row=>body.appendChild(row));
      // Keep non-matching rows in DOM to preserve live actions and checkbox state.
      resultCount.textContent=visible.length+" of "+rows.length+" suppliers";
      if(noMatches)noMatches.hidden=visible.length!==0 || rows.length===0;
    }
    [query,filterField,sortField,direction].forEach(el=>el.addEventListener(el===query?"input":"change",applySupplierView));
    supplierControls.querySelector(".supplier-filter-reset").addEventListener("click",()=>{
      query.value="";filterField.value="all";sortField.value="2";direction.value="asc";applySupplierView();
    });
    const comparison=document.querySelector("#supplier-compare-form");
    if(comparison){
      const toggles=Array.from(supplierTable.querySelectorAll(".supplier-compare-check"));
      const button=comparison.querySelector(".supplier-compare-submit");
      function refreshComparison(){
        const n=toggles.filter(box=>box.checked).length;
        button.disabled=n<2||n>5;
        button.textContent="Compare selected suppliers ("+n+"/5)";
        toggles.forEach(box=>{box.disabled=!box.checked&&n>=5;});
      }
      toggles.forEach(box=>box.addEventListener("change",refreshComparison));
      comparison.addEventListener("submit",event=>{
        if(toggles.filter(box=>box.checked).length<2){event.preventDefault();}
      });
      refreshComparison();
    }
    applySupplierView();
  }


  // DEV-037: mark data-entry forms dirty only after user interaction.
  document.querySelectorAll("form[data-unsaved-guard]").forEach(form=>{
    let dirty=false;
    let submitting=false;
    const markDirty=event=>{
      if(event.target && event.target.matches("input,select,textarea"))dirty=true;
    };
    form.addEventListener("input",markDirty);
    form.addEventListener("change",markDirty);
    // Dynamic field/group/KPI builders update hidden inputs programmatically.
    form.addEventListener("click",event=>{
      if(event.target.closest("#add-field,#add-group,#add-widget,#add-template-field,.field-delete,.group-delete,.widget-remove,.group-up,.group-down,.field-up,.field-down,.icon-delete,.save-template"))dirty=true;
    });
    form.addEventListener("submit",()=>{submitting=true;});
    window.addEventListener("beforeunload",event=>{
      if(dirty&&!submitting){event.preventDefault();event.returnValue="";}
    });
    // Cancel/navigation links get a useful immediate confirmation.
    document.querySelectorAll("a[href]").forEach(link=>{
      link.addEventListener("click",event=>{
        if(!dirty||submitting||event.defaultPrevented||event.metaKey||event.ctrlKey||event.shiftKey||event.altKey||link.target==="_blank")return;
        if(!window.confirm("You have unsaved changes. Leave without saving?"))event.preventDefault();
      });
    });
  });


  // DEV-038: configurable weighted assessment fields.
  const scoreRoot=document.querySelector("#scoring-rules");
  const scoreData=document.querySelector("#scoring-criteria-json");
  const addScore=document.querySelector("#add-scoring-rule");
  if(scoreRoot && scoreData && addScore){
    let scoreRules=parseValue(scoreData);
    const eligible=JSON.parse(scoreRoot.dataset.fields||"[]").filter(f=>["stars","number"].includes(f.type));
    function syncScores(){scoreData.value=JSON.stringify(scoreRules);}
    function renderScores(){
      scoreRoot.replaceChildren();
      scoreRules.forEach((rule,index)=>{
        const row=document.createElement("div");row.className="supplier-score-rule";
        const source=document.createElement("select");source.setAttribute("aria-label","Scoring source field");
        source.appendChild(new Option("Choose assessment field",""));
        eligible.forEach(f=>source.appendChild(new Option(f.fieldName+" ("+f.fieldId+")",f.fieldId)));
        source.value=rule.fieldId||"";
        source.addEventListener("change",()=>{rule.fieldId=source.value;syncScores();});
        const weight=document.createElement("input");
        weight.type="number";weight.min="0.01";weight.max="1000";weight.step="0.01";
        weight.value=rule.weight;weight.setAttribute("aria-label","Scoring weight");
        weight.addEventListener("input",()=>{rule.weight=weight.value;syncScores();});
        const remove=document.createElement("button");remove.type="button";
        remove.className="btn compact danger";remove.textContent="Remove";
        remove.addEventListener("click",()=>{scoreRules.splice(index,1);renderScores();syncScores();});
        row.append(source,weight,remove);scoreRoot.appendChild(row);
      });
      addScore.disabled=scoreRules.length>=12 || eligible.length===0;
    }
    addScore.addEventListener("click",()=>{
      if(scoreRules.length>=12)return;
      const candidate=eligible.find(f=>!scoreRules.some(r=>r.fieldId===f.fieldId));
      if(!candidate)return;
      scoreRules.push({fieldId:candidate.fieldId,weight:1});
      renderScores();syncScores();
    });
    renderScores();
  }


  // UX-052: position row menus outside the scrollable table viewport.
  const supplierRowMenus=[...document.querySelectorAll(".supplier-row-menu")];
  function closeSupplierMenus(except){
    supplierRowMenus.forEach(menu=>{if(menu!==except)menu.open=false;});
  }
  function placeSupplierMenu(menu){
    const trigger=menu.querySelector("summary");
    const dropdown=menu.querySelector(".supplier-row-dropdown");
    if(!trigger||!dropdown)return;
    const box=trigger.getBoundingClientRect();
    const width=205;
    const height=dropdown.offsetHeight||210;
    const left=Math.max(8,Math.min(window.innerWidth-width-8,box.right-width));
    const below=window.innerHeight-box.bottom;
    dropdown.style.left=left+"px";
    dropdown.style.top=(below>=height+12?box.bottom+6:Math.max(8,box.top-height-6))+"px";
  }
  supplierRowMenus.forEach(menu=>menu.addEventListener("toggle",()=>{
    if(menu.open){closeSupplierMenus(menu);placeSupplierMenu(menu);}
  }));
  document.addEventListener("click",event=>{
    if(!event.target.closest(".supplier-row-menu"))closeSupplierMenus();
  });
  document.addEventListener("keydown",event=>{
    if(event.key==="Escape"){
      const active=supplierRowMenus.find(menu=>menu.open);
      if(active){active.open=false;active.querySelector("summary")?.focus();}
    }
  });
  document.querySelectorAll(".supplier-workspace-scroll").forEach(table=>table.addEventListener("scroll",()=>closeSupplierMenus(),{passive:true}));
  window.addEventListener("resize",()=>closeSupplierMenus());

  document.querySelectorAll("[data-copy]").forEach(function(btn){
    btn.addEventListener("click",async function(){const el=document.querySelector(btn.dataset.copy);if(!el)return;await navigator.clipboard.writeText(el.value||el.textContent||"");const old=btn.textContent;btn.textContent="Copied";setTimeout(function(){btn.textContent=old;},1200);});
  });
})();