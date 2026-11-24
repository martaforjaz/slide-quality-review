import {execFileSync} from "node:child_process";
import {readFileSync,writeFileSync} from "node:fs";
import {scan,patchEnergy} from "./site/quality.mjs";

const cohort=JSON.parse(readFileSync("cohort.json","utf8"));
const scored=cohort.map(row=>{
  const raw=execFileSync("python",["-c","from PIL import Image;import struct,sys; im=Image.open(sys.argv[1]).convert('RGBA');sys.stdout.buffer.write(struct.pack('<II', *im.size)+im.tobytes())","cache/patches/"+row.file],{maxBuffer:15*1024*1024});
  const tiles=scan(raw.subarray(8),raw.readUInt32LE(0),raw.readUInt32LE(4));
  return {...row,energy:patchEnergy(tiles),baseline:tiles.length?tiles.some(t=>t.ratio<.2):null};
});
function counts(rows,predict){
  const out={tp:0,fp:0,tn:0,fn:0,abstain:0};
  for(const row of rows){
    const p=predict(row), truth=row.label==="Out of Focus";
    if(p===null)out.abstain++;
    else out[truth?(p?"tp":"fn"):(p?"fp":"tn")]++;
  }
  return out;
}
const calibration=scored.filter(row=>row.split==="calibration");
const test=scored.filter(row=>row.split==="test");
const boundaries=[...new Set(calibration.map(r=>r.energy).filter(x=>x!==null))].sort((a,b)=>a-b);
if(!boundaries.length)throw Error("No calibration tissue");
const thresholds=[0,...boundaries.map((x,i)=>(x+(boundaries[i+1]??x+1))/2)];
const predict=(row,threshold)=>row.energy===null?null:row.energy<threshold;
const positives=calibration.filter(r=>r.label==="Out of Focus").length;
const negatives=calibration.length-positives;
const ranking=thresholds.map(threshold=>{
  const c=counts(calibration,r=>predict(r,threshold));
  return {threshold,score:c.tp/positives+c.tn/negatives,fp:c.fp};
}).sort((a,b)=>b.score-a.score||a.fp-b.fp);
const threshold=ranking[0].threshold;
const baseline=counts(test,r=>r.baseline);
const calibrated=counts(test,r=>predict(r,threshold));
const report={threshold,calibration:calibration.length,test:test.length,baseline,calibrated,
  rows:scored.map(row=>({...row,prediction:predict(row,threshold)}))};
writeFileSync("scanner-results.json",JSON.stringify(report,null,2)+"\n");
console.log(JSON.stringify({threshold,baseline,calibrated}));
