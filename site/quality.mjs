export function scan(rgba, width, height, tile = 64) {
  const gray = new Float32Array(width * height);
  for (let i=0; i<gray.length; i++) gray[i] = .299*rgba[i*4]+.587*rgba[i*4+1]+.114*rgba[i*4+2];
  const tiles = [];
  for (let y=0; y<height; y+=tile) for (let x=0; x<width; x+=tile) {
    const w=Math.min(tile,width-x), h=Math.min(tile,height-y);
    if(w<16 || h<16) continue;
    let tissue=0,sum=0,count=0;
    for(let b=y+1;b<y+h-1;b++) for(let a=x+1;a<x+w-1;a++){
      const i=b*width+a,p=i*4;
      const spread=Math.max(rgba[p],rgba[p+1],rgba[p+2])-Math.min(rgba[p],rgba[p+1],rgba[p+2]);
      if(spread>17 && gray[i]<237) tissue++;
      const lap=4*gray[i]-gray[i-1]-gray[i+1]-gray[i-width]-gray[i+width];
      sum+=lap*lap;count++;
    }
    if(tissue/count>=.22) tiles.push({x,y,w,h,energy:sum/count});
  }
  const values=tiles.map(t=>t.energy).sort((a,b)=>a-b);
  const baseline=values[Math.floor(values.length*.75)] || 0;
  return tiles.map(t=>({...t,ratio:baseline?t.energy/baseline:0}));
}
export function csv(rows) {
  const cell=value=>'"'+String(value).replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"';
  return rows.map(row=>row.map(cell).join(',')).join('\r\n');
}
