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

  document.querySelectorAll("[data-copy]").forEach(function(btn){
    btn.addEventListener("click",async function(){const el=document.querySelector(btn.dataset.copy);if(!el)return;await navigator.clipboard.writeText(el.value||el.textContent||"");const old=btn.textContent;btn.textContent="Copied";setTimeout(function(){btn.textContent=old;},1200);});
  });
})();