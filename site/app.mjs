import { scan, csv, patchAlert } from "./quality.mjs";
const get=id=>document.getElementById(id);
const canvas=get("canvas"), ctx=canvas.getContext("2d",{willReadFrequently:true});
let rows=[], active, overlay=true, busy=false;
const limit=()=>Number(get("threshold").value);
const flagged=row=>row.tiles.filter(t=>t.ratio<limit());
const scannerAlert=row=>get("mode").value==="baseline"
  ? (row.tiles.length ? row.tiles.some(tile=>tile.ratio<.20) : null)
  : patchAlert(row.tiles,row.source.threshold);
async function add(name,src,source) {
  const image=new Image(); image.src=src; await image.decode();
  const scale=Math.min(1,1600/Math.max(image.width,image.height));
  const temp=document.createElement("canvas");
  temp.width=Math.max(1,Math.round(image.width*scale));temp.height=Math.max(1,Math.round(image.height*scale));
  const buffer=temp.getContext("2d");
  buffer.drawImage(image,0,0,temp.width,temp.height);
  const tiles=scan(buffer.getImageData(0,0,temp.width,temp.height).data,temp.width,temp.height);
  rows.push({name,image:temp,tiles,source,decision:"pending"});
}
function render(){
  const priority=row=>row.source ? (scannerAlert(row)===true ? 2 : 0)
    : flagged(row).length/Math.max(1,row.tiles.length);
  const sorted=[...rows].sort((a,b)=>priority(b)-priority(a));
  active ||= sorted[0];
  get("queue").replaceChildren(...sorted.map(row=>{
    const button=document.createElement("button");
    const alert=row.source ? scannerAlert(row) : null;
    const label=row.source ? (alert===null?"No tissue":alert?"Focus alert":"No focus alert") : flagged(row).length+" flagged";
    button.textContent=row.name+" · "+label+" · "+row.decision;
    button.setAttribute("aria-pressed",row===active);
    button.onclick=()=>{active=row;render();};return button;
  }));
  get("export").disabled=!rows.length;
  if(!active)return;
  canvas.width=active.image.width;canvas.height=active.image.height;canvas.hidden=false;
  ctx.drawImage(active.image,0,0);
  if(overlay)for(const {x,y,w,h} of flagged(active)){
    ctx.fillStyle="#ff8c3252";ctx.fillRect(x,y,w,h);ctx.strokeStyle="#c44810";ctx.lineWidth=2;ctx.strokeRect(x+1,y+1,w-2,h-2);
  }
  get("title").textContent=active.name;
  get("summary").textContent=flagged(active).length+" of "+active.tiles.length+" tissue tiles flagged. Review the highlighted regions before deciding.";
  if(active.source){
    const alert=scannerAlert(active);
    get("summary").textContent=(alert===null?"No eligible tissue":alert?"Patch-level focus alert":"No patch-level focus alert")
      + " | Dataset label: "+active.source.label;
  }
  get("decision").disabled=false;get("decision").value=active.decision;
}
async function load(items){
  if(busy)return;
  busy=true;get("files").disabled=get("example").disabled=true;
  let errors=0;
  for(const {name,src,revoke,source} of items){
    try{await add(name,src,source);}catch{errors++;}finally{if(revoke)URL.revokeObjectURL(src);}
  }
  get("status").textContent=rows.length+" images in the queue"+(errors?" · "+errors+" could not be opened":"");
  busy=false;get("files").disabled=get("example").disabled=false;render();
}
get("example").onclick=async()=>{
  if(busy)return;
  if(get("dataset").value==="synthetic"){
    if(!rows.some(row=>row.name==="Example: injected defocus"))await load([{name:"Example: original",src:"reference.png"},{name:"Example: injected defocus",src:"defocus.png"}]);
    return;
  }
  if(rows.some(row=>row.source))return;
  get("status").textContent="Loading scanner examples…";
  try{
    const response=await fetch("scanner-demo.json");
    if(!response.ok)throw Error();
    const dataset=await response.json();
    await load(dataset.examples.map((row,i)=>({name:"TCGA "+(i+1)+" · "+row.organ,src:row.src,source:{threshold:dataset.threshold,label:row.label}})));
  }catch{get("status").textContent="Scanner examples could not be loaded.";}
};
get("files").onchange=e=>{void load([...e.target.files].slice(0,30).map(f=>({name:f.name,src:URL.createObjectURL(f),revoke:true})));e.target.value="";};
get("mode").onchange=render;
get("threshold").oninput=()=>{get("value").textContent=limit().toFixed(2);render();};
get("decision").onchange=e=>{active.decision=e.target.value;render();};
get("toggle").onchange=e=>{overlay=e.target.checked;render();};
get("export").onclick=()=>{
  const rowsForExport=rows.flatMap(row=>{
    const hits=flagged(row);
    return (hits.length?hits:[{}]).map(t=>[row.name,row.decision,row.source?.label??"",row.source?String(scannerAlert(row)):"",row.source?get("mode").value:"",limit(),row.image.width,row.image.height,t.x??"",t.y??"",t.w??"",t.h??""]);
  });
  const link=document.createElement("a");
  link.href=URL.createObjectURL(new Blob([csv([["image","decision","dataset_label","patch_alert","scanner_alert_mode","overlay_threshold","preview_width","preview_height","x","y","width","height"],...rowsForExport])],{type:"text/csv"}));
  link.download="slide-quality-review.csv";link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);
};
render();
