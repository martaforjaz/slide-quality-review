import {execFileSync} from "node:child_process";
import {readFileSync,writeFileSync} from "node:fs";
import {scan,patchEnergy,focusFeatures} from "./site/quality.mjs";
const train=JSON.parse(readFileSync("cohort.json","utf8"));
const test=JSON.parse(readFileSync("holdout.json","utf8"));
if(new Set([...train,...test].map(r=>r.slide)).size!==train.length+test.length) throw Error("Overlapping source slides");
const scored=[...train.map(row=>({...row,split:"train"})),...test].map(row=>{
  const raw=execFileSync("python",["-c","from PIL import Image;import struct,sys;im=Image.open(sys.argv[1]).convert('RGBA');sys.stdout.buffer.write(struct.pack('<II',*im.size)+im.tobytes())","cache/patches/"+row.file],{maxBuffer:15*1024*1024});
  const tiles=scan(raw.subarray(8),raw.readUInt32LE(0),raw.readUInt32LE(4));
  return {...row,features:focusFeatures(tiles),energy:patchEnergy(tiles),original:tiles.length ? tiles.some(tile=>tile.ratio<.2) : null};
});
writeFileSync("cache/focus-features.json",JSON.stringify(scored));
