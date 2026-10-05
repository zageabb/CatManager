(() => {
  const root = document.querySelector("#custom-fields");
  const hidden = document.querySelector("#fields-json");
  const add = document.querySelector("#add-field");

  function esc(v){return String(v).replace(/[&<>"']/g,function(c){return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"}[c];});}
  function slug(v){return v.toLowerCase().replace(/[^a-z0-9]+/g,"_").replace(/^_+|_+$/g,"") || "custom_field";}
  function parse(){if(!hidden)return [];try{return JSON.parse(hidden.value||"[]");}catch(e){return [];}}
  let fields=parse();

  function sync(){if(hidden)hidden.value=JSON.stringify(fields.map(function(f,i){f.order=i+1;return f;}));}
  function render(){
    if(!root)return;
    root.innerHTML="";
    fields.forEach(function(f,index){
      const row=document.createElement("div");
      row.className="field-row custom";
      row.draggable=true;
      row.dataset.index=index;
      const opts=["text","number","dropdown","date"].map(function(x){return '<option value="'+x+'" '+(f.type===x?"selected":"")+'>'+x.charAt(0).toUpperCase()+x.slice(1)+'</option>';}).join("");
      row.innerHTML=
        '<span class="drag" title="Drag to reorder">☰</span>'+
        '<input class="field-name" value="'+esc(f.fieldName||"")+'" placeholder="Field name">'+
        '<select class="field-kind">'+opts+'</select>'+
        '<input class="field-options '+(f.type==="dropdown"?"":"hidden")+'" value="'+esc((f.options||[]).join(", "))+'" placeholder="Dropdown options, comma separated">'+
        '<label class="required-toggle"><input type="checkbox" '+(f.required?"checked":"")+'> Required</label>'+
        '<button type="button" class="icon-delete" aria-label="Delete">×</button>';
      row.querySelector(".field-name").addEventListener("input",function(e){
        fields[index].fieldName=e.target.value;
        if(!fields[index].fieldId || fields[index]._generated){fields[index].fieldId=slug(e.target.value);fields[index]._generated=true;}
        sync();
      });
      row.querySelector(".field-kind").addEventListener("change",function(e){
        fields[index].type=e.target.value;
        if(e.target.value!=="dropdown")fields[index].options=[];
        render();sync();
      });
      row.querySelector(".field-options").addEventListener("input",function(e){fields[index].options=e.target.value.split(",").map(function(x){return x.trim();}).filter(Boolean);sync();});
      row.querySelector(".required-toggle input").addEventListener("change",function(e){fields[index].required=e.target.checked;sync();});
      row.querySelector(".icon-delete").addEventListener("click",function(){fields.splice(index,1);render();sync();});
      row.addEventListener("dragstart",function(e){e.dataTransfer.setData("text/plain",String(index));});
      row.addEventListener("dragover",function(e){e.preventDefault();});
      row.addEventListener("drop",function(e){e.preventDefault();const from=Number(e.dataTransfer.getData("text/plain"));const moved=fields.splice(from,1)[0];fields.splice(index,0,moved);render();sync();});
      root.appendChild(row);
    });
  }
  if(add)add.addEventListener("click",function(){fields.push({fieldId:"custom_field_"+(fields.length+1),fieldName:"",type:"text",options:[],required:false,_generated:true});render();sync();});
  render();sync();

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

  document.querySelectorAll("[data-copy]").forEach(function(btn){
    btn.addEventListener("click",async function(){const el=document.querySelector(btn.dataset.copy);if(!el)return;await navigator.clipboard.writeText(el.value||el.textContent||"");const old=btn.textContent;btn.textContent="Copied";setTimeout(function(){btn.textContent=old;},1200);});
  });
})();