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
    renderFields();sync();
  });
  loadFieldTemplates();

  function sync(){
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
      row.querySelector(".group-name").addEventListener("input",function(e){groups[index].name=e.target.value;renderFields();sync();});
      row.querySelector(".group-up").addEventListener("click",function(){if(index<1)return;const moved=groups.splice(index,1)[0];groups.splice(index-1,0,moved);renderGroups();renderFields();sync();});
      row.querySelector(".group-down").addEventListener("click",function(){if(index>=groups.length-1)return;const moved=groups.splice(index,1)[0];groups.splice(index+1,0,moved);renderGroups();renderFields();sync();});
      row.querySelector(".group-delete").addEventListener("click",function(){
        const gid=g.groupId;
        fields.forEach(function(field){if(field.groupId===gid)field.groupId="";});
        groups.splice(index,1);
        renderGroups();renderFields();sync();
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
      const opts=["text","number","dropdown","date","boolean"].map(function(x){return '<option value="'+x+'" '+(f.type===x?"selected":"")+'>'+x.charAt(0).toUpperCase()+x.slice(1)+'</option>';}).join("");
      row.innerHTML=
        '<span class="drag" title="Drag to reorder">☰</span>'+
        '<input class="field-name" value="'+esc(f.fieldName||"")+'" placeholder="Field name">'+
        '<select class="field-kind">'+opts+'</select>'+
        '<select class="field-group" aria-label="Field group">'+groupOptions(f.groupId||"")+'</select>'+
        '<input class="field-options '+(f.type==="dropdown"?"":"hidden")+'" value="'+esc((f.options||[]).join(", "))+'" placeholder="Dropdown options, comma separated">'+
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
        if(e.target.value!=="dropdown")fields[index].options=[];
        renderFields();sync();
      });
      row.querySelector(".field-group").addEventListener("change",function(e){fields[index].groupId=e.target.value;sync();});
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
      row.querySelector(".icon-delete").addEventListener("click",function(){fields.splice(index,1);renderFields();sync();});
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
    renderGroups();renderFields();sync();
  });
  renderGroups();renderFields();sync();


  const widgetRoot=document.querySelector("#dashboard-widgets");
  const widgetHidden=document.querySelector("#dashboard-widgets-json");
  const addWidget=document.querySelector("#add-widget");
  let widgets=parseValue(widgetHidden);
  const widgetMetrics=["count","count_where","sum","average","minimum","maximum","distinct","ratio","percentage"];
  const availableWidgetFields=[{fieldId:"supplierId",fieldName:"Supplier ID"},
    {fieldId:"supplierName",fieldName:"Supplier Name"}]
    .concat(widgetRoot ? JSON.parse(widgetRoot.dataset.fields||"[]") : []);
  function fieldSelect(current){
    return '<option value="">Choose field…</option>'+availableWidgetFields.map(function(f){
      return '<option value="'+esc(f.fieldId)+'" '+(f.fieldId===current?"selected":"")+'>'+esc(f.fieldName)+'</option>';
    }).join("");
  }
  function renderWidgets(){
    if(!widgetRoot)return;
    widgetRoot.innerHTML="";
    widgets.forEach(function(w,i){
      const row=document.createElement("div");
      row.className="field-row custom widget-row";
      row.innerHTML='<input class="widget-title" aria-label="Widget title" placeholder="KPI title" value="'+esc(w.title||"")+'">'+
        '<select class="widget-metric" aria-label="Calculation">'+widgetMetrics.map(function(m){return '<option value="'+m+'" '+(w.metric===m?"selected":"")+'>'+m.replace("_"," ")+'</option>';}).join("")+'</select>'+
        '<select class="widget-field" aria-label="Source field">'+fieldSelect(w.fieldId||"")+'</select>'+
        '<select class="widget-other" aria-label="Denominator field">'+fieldSelect(w.otherFieldId||"")+'</select>'+
        '<input class="widget-match" aria-label="Count matching value" placeholder="Equals..." value="'+esc(w.match||"")+'">'+
        '<select class="widget-format" aria-label="Display format">'+["number","currency","percentage"].map(function(f){return '<option '+(w.format===f?"selected":"")+'>'+f+'</option>';}).join("")+'</select>'+
        '<select class="widget-display" aria-label="Display location">'+["panel","supplier","both"].map(function(d){return '<option value="'+d+'" '+((w.display||"panel")===d?"selected":"")+'>'+({panel:"Panel KPI",supplier:"Supplier column",both:"Both"}[d])+'</option>';}).join("")+'</select>'+
        '<button class="btn compact danger widget-remove" type="button">Remove</button>';
      [[".widget-title","title"],[".widget-metric","metric"],[".widget-field","fieldId"],
       [".widget-other","otherFieldId"],[".widget-match","match"],[".widget-format","format"],[".widget-display","display"]].forEach(function(item){
        row.querySelector(item[0]).addEventListener("change",function(e){w[item[1]]=e.target.value;syncWidgets();renderWidgets();});
      });
      row.querySelector(".widget-title").addEventListener("input",function(e){w.title=e.target.value;syncWidgets();});
      row.querySelector(".widget-match").addEventListener("input",function(e){w.match=e.target.value;syncWidgets();});
      row.querySelector(".widget-other").hidden=!["ratio","percentage"].includes(w.metric);
      row.querySelector(".widget-match").hidden=w.metric!=="count_where";
      row.querySelector(".widget-field").hidden=w.metric==="count";
      row.querySelector(".widget-remove").addEventListener("click",function(){widgets.splice(i,1);renderWidgets();syncWidgets();});
      widgetRoot.appendChild(row);
    });
    if(addWidget)addWidget.disabled=widgets.length>=6;
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

  document.querySelectorAll("[data-copy]").forEach(function(btn){
    btn.addEventListener("click",async function(){const el=document.querySelector(btn.dataset.copy);if(!el)return;await navigator.clipboard.writeText(el.value||el.textContent||"");const old=btn.textContent;btn.textContent="Copied";setTimeout(function(){btn.textContent=old;},1200);});
  });
})();