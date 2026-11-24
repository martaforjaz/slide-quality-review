import {execFileSync} from "node:child_process";
import {scan,csv} from "./site/quality.mjs";
import assert from "node:assert/strict";
const files=["reference","defocus"];
const result={};
for(const name of files){
  const rgba=execFileSync("python",["-c","from PIL import Image;import sys;sys.stdout.buffer.write(Image.open(sys.argv[1]).convert('RGBA').tobytes())","site/"+name+".png"],{maxBuffer:2*1024*1024});
  const tiles=scan(rgba,512,512), hits=tiles.filter(t=>t.ratio<.20);
  const inside=t=>t.x>=128&&t.x<320&&t.y>=128&&t.y<320;
  result[name]={tissue_tiles:tiles.length,alerts:hits.length,inside_injected_region:hits.filter(inside).length};
}
assert.equal(scan(new Uint8Array(64*64*4).fill(255),64,64).length,0);
assert.equal(csv([["=unsafe",'a"b']]),'"\'=unsafe","a""b"');
assert(result.defocus.inside_injected_region>result.reference.inside_injected_region);
console.log(JSON.stringify(result,null,2));
