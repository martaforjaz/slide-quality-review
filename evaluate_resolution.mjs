// Measure frozen detector performance after downsampling the same holdout patches.
import {execFileSync} from "node:child_process";
import {readFileSync,writeFileSync} from "node:fs";
import {scan,patchEnergy,combinedAlert} from "./site/quality.mjs";
const holdout=JSON.parse(readFileSync("holdout-results.json","utf8"));
const threshold=JSON.parse(readFileSync("scanner-results.json","utf8")).threshold;
const report={native:holdout.methods};
for(const factor of [2,4]){
  const counts=Object.fromEntries(["original","calibrated","combined"].map(m=>[m,{tp:0,tn:0,fp:0,fn:0,abstain:0}]));
  for(const row of holdout.rows){
    const raw=execFileSync("python",["-c","from PIL import Image;import struct,sys;im=Image.open(sys.argv[1]).convert('RGBA');f=int(sys.argv[2]);im=im.resize((im.width//f,im.height//f),Image.Resampling.LANCZOS);sys.stdout.buffer.write(struct.pack('<II',*im.size)+im.tobytes())","cache/patches/"+row.file,String(factor)],{maxBuffer:16*1024*1024});
    const tiles=scan(raw.subarray(8),raw.readUInt32LE(0),raw.readUInt32LE(4));
    const energy=patchEnergy(tiles), truth=row.label==="Out of Focus";
    const preds={original:tiles.length?tiles.some(t=>t.ratio<.2):null,calibrated:energy===null?null:energy<threshold,combined:combinedAlert(tiles,holdout.model)};
    for(const [mode,p] of Object.entries(preds))counts[mode][p===null?"abstain":truth?(p?"tp":"fn"):(p?"fp":"tn")]++;
  }
  report["downsample_"+factor]=counts;
}
writeFileSync("resolution-results.json",JSON.stringify(report,null,2)+"\n");
console.log(JSON.stringify(report));


