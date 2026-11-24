export function scan(rgba, width, height, tile = 64) {
  const gray = new Float32Array(width * height);
  for (let i=0; i<gray.length; i++) gray[i] = .299*rgba[i*4]+.587*rgba[i*4+1]+.114*rgba[i*4+2];
  const tiles = [];
  for (let y=0; y<height; y+=tile) for (let x=0; x<width; x+=tile) {
    const w=Math.min(tile,width-x), h=Math.min(tile,height-y);
    if(w<16 || h<16) continue;
    let tissue=0,sum=0,gradient=0,count=0;
    for(let b=y+1;b<y+h-1;b++) for(let a=x+1;a<x+w-1;a++){
      const i=b*width+a,p=i*4;
      const spread=Math.max(rgba[p],rgba[p+1],rgba[p+2])-Math.min(rgba[p],rgba[p+1],rgba[p+2]);
      if(spread>17 && gray[i]<237) tissue++;
      const lap=4*gray[i]-gray[i-1]-gray[i+1]-gray[i-width]-gray[i+width];
      sum+=lap*lap;
      gradient+=(gray[i+1]-gray[i-1])**2+(gray[i+width]-gray[i-width])**2;
      count++;
    }
    if(tissue/count>=.22) tiles.push({x,y,w,h,energy:sum/count,gradient:gradient/count});
  }
  const values=tiles.map(t=>t.energy).sort((a,b)=>a-b);
  const baseline=values[Math.floor(values.length*.75)] || 0;
  return tiles.map(t=>({...t,ratio:baseline?t.energy/baseline:0}));
}
export function csv(rows) {
  const cell=value=>'"'+String(value).replace(/^[=+\-@\t\r]/,"'$&").replaceAll('"','""')+'"';
  return rows.map(row=>row.map(cell).join(',')).join('\r\n');
}
export function patchEnergy(tiles) {
  const values=tiles.map(tile=>tile.energy).sort((a,b)=>a-b);
  return values.length ? values[Math.floor(values.length/2)] : null;
}

export function patchAlert(tiles, threshold) {
  const energy=patchEnergy(tiles);
  return energy===null ? null : energy<threshold;
}

export function focusFeatures(tiles) {
  if (!tiles.length) return null;
  const energies=tiles.map(t=>t.energy).sort((a,b)=>a-b);
  const quantile=(xs,q)=>xs[Math.floor((xs.length-1)*q)];
  const median=quantile(energies,.5);
  const ratios=tiles.map(t=>t.energy/(1+t.gradient)).sort((a,b)=>a-b);
  return [Math.log1p(median), Math.log1p(quantile(energies,.25)),
    Math.log1p(quantile(ratios,.5)), Math.log1p(quantile(energies,.75))-Math.log1p(median)];
}

export function combinedAlert(tiles, model) {
  const features=focusFeatures(tiles);
  if (!features) return null;
  return features.reduce((score,value,i)=>score+((value-model.mean[i])/model.scale[i])*model.weights[i],model.intercept)>=0;
}
