const $ = (id) => document.getElementById(id);
const yen = (v) => Number.isFinite(v) ? new Intl.NumberFormat('ja-JP',{style:'currency',currency:'JPY',maximumFractionDigits:0}).format(v) : '—';
const pct = (v) => Number.isFinite(v) ? `${(v*100).toFixed(1)}%` : '—';
const clamp = (v,a,b) => Math.max(a,Math.min(b,v));
let market = null;
let chart = null;
let files = [];
let photoScore = null;

const samples = {
  TA5091:{code:'TA5091',address:'東京都新宿区若松町36-15',station:'早稲田',walk:6,sqm:17.34,bedrooms:0,accommodates:2,rent:118800,management:11000,keyMoney:4,deposit:3,otherInitial:1.5,setup:700000,interior:'standard'},
  TA5092:{code:'TA5092',address:'東京都杉並区上井草3丁目32-7',station:'上井草',walk:1,sqm:37.8,bedrooms:1,accommodates:4,rent:108900,management:9900,keyMoney:5,deposit:1,otherInitial:1.5,setup:800000,interior:'renovated'},
  TA5088:{code:'TA5088',address:'東京都世田谷区南烏山6丁目29-9',station:'千歳烏山',walk:5,sqm:32.2,bedrooms:1,accommodates:3,rent:143000,management:11000,keyMoney:4,deposit:3,otherInitial:1.5,setup:800000,interior:'standard'}
};

async function loadMarket(){
  try{
    const res=await fetch('/data/tokyo_market.json',{cache:'no-cache'});
    if(!res.ok) throw new Error('dataset unavailable');
    market=await res.json();
    $('dataStatus').textContent=`FREE DATA · Inside Airbnb ${market.snapshot} · ${market.cells.length.toLocaleString()} segments`;
    $('dataStatus').style.color='#d9ff43';
  }catch(err){
    $('dataStatus').textContent='市場データ未生成 · GitHub Actionを実行してください';
    $('dataStatus').style.color='#ffbd4a';
  }
}
loadMarket();

for(const button of document.querySelectorAll('[data-sample]')){
  button.addEventListener('click',()=>applySample(samples[button.dataset.sample]));
}
function applySample(s){
  for(const [key,value] of Object.entries(s)) if($(key)) $(key).value=value;
  window.scrollTo({top:document.querySelector('.workspace').offsetTop-80,behavior:'smooth'});
}

const dropzone=$('dropzone');
$('flyerInput').addEventListener('change',(e)=>setFiles([...e.target.files]));
['dragenter','dragover'].forEach(name=>dropzone.addEventListener(name,e=>{e.preventDefault();dropzone.classList.add('drag')}));
['dragleave','drop'].forEach(name=>dropzone.addEventListener(name,e=>{e.preventDefault();dropzone.classList.remove('drag')}));
dropzone.addEventListener('drop',e=>setFiles([...e.dataTransfer.files].filter(f=>f.type.startsWith('image/'))));

async function setFiles(next){
  files=next.slice(0,6);
  $('thumbs').innerHTML='';
  for(const file of files){
    const img=document.createElement('img'); img.src=URL.createObjectURL(file); $('thumbs').appendChild(img);
  }
  photoScore=files.length ? await analyzePhotoQuality(files[0]) : null;
  $('ocrStatus').textContent=photoScore==null?'':`画像品質 ${photoScore}/100`;
}

async function analyzePhotoQuality(file){
  const bitmap=await createImageBitmap(file);
  const w=160,h=Math.max(80,Math.round(160*bitmap.height/bitmap.width));
  const c=document.createElement('canvas'); c.width=w;c.height=h;
  const ctx=c.getContext('2d',{willReadFrequently:true}); ctx.drawImage(bitmap,0,0,w,h);
  const d=ctx.getImageData(0,0,w,h).data;
  let lum=0,lum2=0,edge=0,n=0;
  const gray=new Float32Array(w*h);
  for(let i=0,p=0;i<d.length;i+=4,p++){const g=.2126*d[i]+.7152*d[i+1]+.0722*d[i+2];gray[p]=g;lum+=g;lum2+=g*g;n++;}
  const mean=lum/n,sd=Math.sqrt(Math.max(0,lum2/n-mean*mean));
  for(let y=1;y<h;y++)for(let x=1;x<w;x++){const p=y*w+x;edge+=Math.abs(gray[p]-gray[p-1])+Math.abs(gray[p]-gray[p-w]);}
  edge/=((w-1)*(h-1)*2);
  const brightness=1-Math.min(1,Math.abs(mean-150)/150);
  const contrast=clamp(sd/65,0,1);
  const sharp=clamp(edge/32,0,1);
  return Math.round(100*(.35*brightness+.30*contrast+.35*sharp));
}

$('ocrButton').addEventListener('click',async()=>{
  if(!files.length){$('ocrStatus').textContent='画像を追加してください';return;}
  if(!window.Tesseract){$('ocrStatus').textContent='OCRライブラリを読み込めません';return;}
  const btn=$('ocrButton');btn.disabled=true;$('ocrStatus').textContent='OCR解析中…';
  try{
    const {data:{text}}=await Tesseract.recognize(files[0],'jpn+eng',{logger:m=>{if(m.progress)$('ocrStatus').textContent=`OCR ${Math.round(m.progress*100)}%`;}});
    applyOcr(text);$('ocrStatus').textContent='OCR入力済み。値を確認してください';
  }catch(e){$('ocrStatus').textContent='OCR失敗。手入力してください';}
  finally{btn.disabled=false;}
});
function applyOcr(text){
  const clean=text.replace(/\r/g,'');
  const addr=clean.match(/東京都[^\n]{4,42}/);if(addr)$('address').value=addr[0].replace(/\s+/g,'');
  const rent=clean.match(/(?:賃料|家賃)[^\d]{0,12}([\d,.]+)\s*(万円|円)/);if(rent)$('rent').value=toYen(rent[1],rent[2]);
  const mg=clean.match(/(?:管理費|共益費)[^\d]{0,12}([\d,.]+)\s*(万円|円)/);if(mg)$('management').value=toYen(mg[1],mg[2]);
  const area=clean.match(/(?:専有面積|面積)[^\d]{0,12}([\d.]+)\s*[m㎡]/i);if(area)$('sqm').value=area[1];
  const walk=clean.match(/徒歩\s*([0-9０-９]+)\s*分/);if(walk)$('walk').value=normalizeDigits(walk[1]);
  const station=clean.match(/([一-龠ぁ-んァ-ヶA-Za-z0-9０-９]+駅)/);if(station)$('station').value=station[1].replace(/駅$/,'');
}
function normalizeDigits(s){return s.replace(/[０-９]/g,c=>String.fromCharCode(c.charCodeAt(0)-0xFEE0));}
function toYen(v,u){const n=Number(String(v).replace(/,/g,''));return Math.round(n*(u==='万円'?10000:1));}

$('legalMode').addEventListener('change',()=>{if($('legalMode').value==='housing_act')$('sellableNights').value=180;if($('legalMode').value==='hotel_act')$('sellableNights').value=365;});

async function geocode(address){
  const res=await fetch('/api/geocode',{method:'POST',headers:{'content-type':'application/json'},body:JSON.stringify({address})});
  if(!res.ok) throw new Error('住所から座標を取得できませんでした');
  return res.json();
}
function haversine(a,b,c,d){const r=6371,rad=Math.PI/180;const p1=a*rad,p2=c*rad;const dp=(c-a)*rad,dl=(d-b)*rad;const x=Math.sin(dp/2)**2+Math.cos(p1)*Math.cos(p2)*Math.sin(dl/2)**2;return 2*r*Math.atan2(Math.sqrt(x),Math.sqrt(1-x));}
function bucket(b){const n=Number(b);return n<=0?'0':n===1?'1':n===2?'2':'3+';}
function nearestCell(lat,lon,bed){
  const wanted=bucket(bed);
  let candidates=market.cells.filter(c=>c.bed===wanted&&c.count>=5);
  if(!candidates.length)candidates=market.cells.filter(c=>c.bed==='all');
  let best=null,dist=Infinity;for(const c of candidates){const d=haversine(lat,lon,c.lat,c.lon);if(d<dist){best=c;dist=d;}}
  if(best&&dist>2.6){let all=market.cells.filter(c=>c.bed==='all');for(const c of all){const d=haversine(lat,lon,c.lat,c.lon);if(d<dist){best=c;dist=d;}}}
  return {cell:best,distance:dist};
}
function quantile(values,q){const a=values.filter(Number.isFinite).sort((x,y)=>x-y);if(!a.length)return NaN;const p=(a.length-1)*q,l=Math.floor(p),h=Math.ceil(p);return a[l]+(a[h]-a[l])*(p-l);}
function mean(a){const x=a.filter(Number.isFinite);return x.length?x.reduce((s,v)=>s+v,0)/x.length:NaN;}
function std(a){const m=mean(a),x=a.filter(Number.isFinite);return x.length>1?Math.sqrt(x.reduce((s,v)=>s+(v-m)**2,0)/(x.length-1)):0;}
function adjustment(p){let occ=1,adr=1;if(Number.isFinite(p.walk)){occ*=clamp(1.04-.008*Math.max(p.walk-3,0),.88,1.04);adr*=clamp(1.03-.006*Math.max(p.walk-3,0),.90,1.03);}const g={basic:[.94,.90],standard:[1,1],renovated:[1.04,1.08],premium:[1.06,1.16]}[p.interior]||[1,1];occ*=g[0];adr*=g[1];if(photoScore!=null){const f=.97+(photoScore/100)*.06;occ*=f;adr*=f;}return{occ,adr};}
function readProperty(){const n=id=>Number($(id).value||0);return{code:$('code').value.trim()||'PROPERTY',address:$('address').value.trim(),station:$('station').value.trim(),walk:n('walk'),sqm:n('sqm'),bedrooms:n('bedrooms'),accommodates:n('accommodates'),interior:$('interior').value,rent:n('rent'),management:n('management'),utilities:n('utilities'),setup:n('setup'),keyMoney:n('keyMoney'),deposit:n('deposit'),otherInitial:n('otherInitial'),variableRate:n('variableRate')/100,legalMode:$('legalMode').value,sellableNights:n('sellableNights'),permission:$('permission').value,zoning:$('zoning').value};}

$('propertyForm').addEventListener('submit',async e=>{
  e.preventDefault();const btn=$('analyzeButton');btn.disabled=true;btn.firstChild.textContent='分析中… ';
  try{
    if(!market)throw new Error('市場データがまだ生成されていません。しばらくして再読込してください。');
    const p=readProperty();if(!p.address)throw new Error('住所を入力してください');
    const geo=await geocode(p.address);const found=nearestCell(Number(geo.lat),Number(geo.lon),p.bedrooms);if(!found.cell)throw new Error('近隣市場データが見つかりません');
    const result=underwrite(p,found.cell,found.distance,geo);render(p,result);
  }catch(err){alert(err.message||String(err));}
  finally{btn.disabled=false;btn.firstChild.textContent='分析する ';}
});

function underwrite(p,cell,distance,geo){
  const adj=adjustment(p);const months=cell.months.map(m=>({month:m[0],mean:m[1],std:m[2]||0,p10:m[3],p50:m[4],p90:m[5],active:m[6]}));const recent=months.slice(-24);const monthlyMeans=recent.map(m=>m.mean);
  const occ50=clamp(quantile(monthlyMeans,.5)*adj.occ,.03,.92),occ10=clamp(quantile(monthlyMeans,.1)*adj.occ,.02,occ50),occ90=clamp(quantile(monthlyMeans,.9)*adj.occ,occ50,.95),occMean=clamp(mean(monthlyMeans)*adj.occ,.02,.95),occStd=std(monthlyMeans);
  const prices=cell.price.map(Number);const adr10=Math.max(2500,prices[0]*adj.adr),adr50=prices[1]*adj.adr,adr90=prices[2]*adj.adr;
  const initial=p.setup+(p.keyMoney+p.deposit+p.otherInitial)*p.rent;const fixedAnnual=(p.rent+p.management+p.utilities)*12;const revenue=(occ,adr)=>Math.min(occ*365,p.sellableNights||365)*adr;const gross10=revenue(occ10,adr10),gross50=revenue(occ50,adr50),gross90=revenue(occ90,adr90);const cash50=gross50*(1-p.variableRate)-fixedAnnual;const roi=initial>0?cash50/initial:null;const payback=initial>0&&cash50>0?initial/(cash50/12):null;
  const econMargin=cash50/Math.max(fixedAnnual,1);const econ=clamp(50+econMargin*65,0,100);const demand=clamp((occ50/.70)*62+Math.min(adr50/30000,1)*38,0,100);const sample=clamp(cell.count/35*100,0,100);let legal=p.legalMode==='unknown'?35:70;if(p.permission==='yes')legal+=18;if(p.zoning==='checked')legal+=12;if(p.permission==='no')legal=0;legal=clamp(legal,0,100);const evidenceScore=cell.count>=20?78:cell.count>=10?65:50;let score=.36*econ+.24*demand+.15*sample+.15*legal+.10*evidenceScore;let hardStop=p.permission==='no'||cash50<0;let grade=hardStop?'D':score>=80?'A':score>=65?'B':score>=50?'C':'D';
  const ward=p.address.match(/東京都([^市区町村]{1,8}[区市町村])/);const risks=[];if(p.permission==='unknown')risks.push('貸主・管理規約の民泊承諾が未確認。契約前の書面確認が必要。');if(p.zoning==='unknown')risks.push('用途地域・区条例を未確認。自治体の営業曜日制限で販売可能泊数が減る可能性。');if(p.legalMode==='housing_act')risks.push('民泊新法は全国上限180日/年。区条例でさらに減る場合がある。');if(p.legalMode==='unknown')risks.push('許可方式が未確定。住宅宿泊事業法と旅館業では営業可能日数・設備要件が異なる。');risks.push('無料モードの稼働率はレビュー時系列からのproxyで、競合の予約台帳ではない。');risks.push('過去の実現ADRは公開データだけでは復元できず、現在Comparable価格をproxy使用。');if(distance>1.7)risks.push(`十分近いComparableセルが薄く、代表点まで${distance.toFixed(1)}km。精度を割り引く必要。`);
  const reasons=[`周辺Comparable ${cell.count}件 / セル中心まで${distance.toFixed(2)}km。`,`過去24か月の月次稼働率proxy中央値 ${pct(occ50)}、月間平均の標準偏差 ${pct(occStd)}。`,`現在Comparable ADR proxy中央値 ${yen(adr50)}。`,`P50売上 ${yen(gross50)} に対し固定費 ${yen(fixedAnnual)}/年。`,photoScore==null?'画像補正なし。':'画像の明るさ・コントラスト・シャープネス品質 '+photoScore+'/100 を小幅補正に使用。'];
  const confidence=clamp(.42+Math.min(cell.count,35)/100+(recent.length/24)*.08-(distance>1.7?.10:0),.35,.82);
  return{cell,distance,geo,months,occ10,occ50,occ90,occMean,occStd,adr10,adr50,adr90,gross10,gross50,gross90,cash50,roi,payback,initial,fixedAnnual,score:clamp(score,0,100),grade,hardStop,risks,reasons,confidence,ward:ward?ward[1]:null,booked50:Math.min(occ50*365,p.sellableNights||365)};
}

function render(p,r){$('emptyState').hidden=true;$('results').hidden=false;$('resultCode').textContent=p.code;$('resultAddress').textContent=p.address;$('resultMeta').textContent=`${p.station?`${p.station}駅 徒歩${p.walk}分 · `:''}${p.sqm}㎡ · ${p.bedrooms===0?'Studio':p.bedrooms+'BR'} · ${p.accommodates}名`;const g=$('grade');g.querySelector('b').textContent=r.grade;g.querySelector('span').textContent=`${Math.round(r.score)} / 100`;g.querySelector('b').style.color=r.grade==='A'?'#5de18a':r.grade==='B'?'#73a5ff':r.grade==='C'?'#ffbd4a':'#ff5f62';$('occ50').textContent=pct(r.occ50);$('occRange').textContent=`P10 ${pct(r.occ10)} / P90 ${pct(r.occ90)}`;$('adr50').textContent=yen(r.adr50);$('adrRange').textContent=`P10 ${yen(r.adr10)} / P90 ${yen(r.adr90)}`;$('revenue50').textContent=yen(r.gross50);$('bookedNights').textContent=`推定販売 ${Math.round(r.booked50)}泊 / 上限${p.sellableNights}泊`;$('cashflow50').textContent=yen(r.cash50);$('roi').textContent=r.roi==null?'ROI —':`ROI ${(r.roi*100).toFixed(1)}% · ${r.payback?`回収 ${r.payback.toFixed(1)}か月`:'回収不可'}`;$('historyStats').textContent=`平均 ${pct(r.occMean)} · σ ${pct(r.occStd)}`;$('reasons').innerHTML=r.reasons.map(x=>`<li>${escapeHtml(x)}</li>`).join('');$('risks').innerHTML=r.risks.map(x=>`<li>${escapeHtml(x)}</li>`).join('');$('compSummary').innerHTML=`<div class="finance-row"><span>市場セル</span><b>${r.cell.key} / ${r.cell.bed}BR</b></div><div class="finance-row"><span>Comparable</span><b>${r.cell.count}件</b></div><div class="finance-row"><span>Evidence confidence</span><b>${pct(r.confidence)}</b></div>`;renderComps(r.cell.examples||[],r.geo.lat,r.geo.lon);$('finance').innerHTML=[['初期投資',yen(r.initial)],['年間固定費',yen(r.fixedAnnual)],['売上 P10',yen(r.gross10)],['売上 P50',yen(r.gross50)],['売上 P90',yen(r.gross90)],['CF P50',yen(r.cash50)],['ROI P50',r.roi==null?'—':`${(r.roi*100).toFixed(1)}%`],['回収期間',r.payback?`${r.payback.toFixed(1)}か月`:'回収不可']].map(([a,b])=>`<div class="finance-row"><span>${a}</span><b>${b}</b></div>`).join('');$('evidence').textContent=`Inside Airbnb ${market.snapshot} / 過去${market.months}か月 review-model proxy。Review rate ${market.method.review_rate}、fallback stay ${market.method.default_stay_nights}泊、proxy上限${pct(market.method.occupancy_cap)}。ADRは現在価格proxy。数値は実測予約台帳ではありません。`;drawChart(r.months);$('resultPanel').scrollIntoView({behavior:'smooth',block:'start'});window.lastAnalysis={property:p,result:r};}
function renderComps(items,lat,lon){$('comps').innerHTML=items.slice(0,6).map(c=>{const d=haversine(Number(lat),Number(lon),c.lat,c.lon);return`<div class="comp"><div><b>${escapeHtml(c.name||'Airbnb')}</b><br><span>${d.toFixed(2)}km · ${c.bedrooms??'—'}BR · ${c.accommodates??'—'}名 · ${c.reviews_ltm??0} reviews/12m</span></div><a target="_blank" rel="noopener" href="https://www.airbnb.com/rooms/${c.id}">${yen(c.price)}</a></div>`}).join('')||'<span style="color:#9098a3;font-size:10px">Comparable例はこのセグメントでは未収録</span>';}
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}
function drawChart(months){const ctx=$('historyChart');if(chart)chart.destroy();const labels=months.map(m=>m.month);const data=months.map(m=>m.mean*100);const upper=months.map(m=>clamp(m.mean+(m.std||0),0,1)*100);const lower=months.map(m=>clamp(m.mean-(m.std||0),0,1)*100);chart=new Chart(ctx,{type:'line',data:{labels,datasets:[{label:'+1σ',data:upper,borderWidth:0,pointRadius:0,backgroundColor:'rgba(217,255,67,.10)',fill:'+1'},{label:'平均',data,borderColor:'#d9ff43',backgroundColor:'#d9ff43',pointRadius:1.5,borderWidth:2,tension:.25},{label:'-1σ',data:lower,borderWidth:0,pointRadius:0,fill:false}]},options:{responsive:true,maintainAspectRatio:true,plugins:{legend:{display:false}},scales:{x:{grid:{display:false},ticks:{color:'#717985',maxTicksLimit:12,font:{size:9}}},y:{min:0,max:80,grid:{color:'#272d34'},ticks:{color:'#717985',callback:v=>v+'%',font:{size:9}}}}}});}

$('exportButton').addEventListener('click',()=>{if(!window.lastAnalysis)return;exportSummary(window.lastAnalysis.property,window.lastAnalysis.result);});
function exportSummary(p,r){const c=document.createElement('canvas');c.width=1600;c.height=900;const x=c.getContext('2d');x.fillStyle='#0b0d10';x.fillRect(0,0,c.width,c.height);x.fillStyle='#d9ff43';x.fillRect(70,62,54,54);x.fillStyle='#0b0d10';x.font='900 24px sans-serif';x.fillText('MU',79,98);x.fillStyle='#f3f1ea';x.font='800 28px sans-serif';x.fillText('MINPAKU UNDERWRITER',145,96);x.fillStyle='#9098a3';x.font='18px sans-serif';x.fillText(`${p.code} · ${p.address}`,70,160);x.fillStyle=r.grade==='A'?'#5de18a':r.grade==='B'?'#73a5ff':r.grade==='C'?'#ffbd4a':'#ff5f62';x.font='900 150px sans-serif';x.fillText(r.grade,1310,185);x.fillStyle='#f3f1ea';x.font='900 46px sans-serif';x.fillText(`${Math.round(r.score)} / 100`,1285,235);const blocks=[['OCCUPANCY P50',pct(r.occ50),'P10 '+pct(r.occ10)+'  /  P90 '+pct(r.occ90)],['ADR P50',yen(r.adr50),'P10 '+yen(r.adr10)+'  /  P90 '+yen(r.adr90)],['GROSS REVENUE',yen(r.gross50),`${Math.round(r.booked50)} booked nights`],['ANNUAL CASH FLOW',yen(r.cash50),r.roi==null?'ROI —':`ROI ${(r.roi*100).toFixed(1)}%`]];let y=290;for(const [lab,val,sub] of blocks){x.fillStyle='#151a20';x.fillRect(70,y,680,112);x.fillStyle='#9098a3';x.font='700 17px sans-serif';x.fillText(lab,95,y+32);x.fillStyle='#f3f1ea';x.font='800 34px sans-serif';x.fillText(val,95,y+74);x.fillStyle='#9098a3';x.font='15px sans-serif';x.fillText(sub,390,y+72);y+=126;}x.fillStyle='#151a20';x.fillRect(790,290,740,490);x.fillStyle='#f3f1ea';x.font='800 24px sans-serif';x.fillText('KEY RISKS / UNKNOWNS',825,335);x.font='18px sans-serif';let ry=380;for(const risk of r.risks.slice(0,6)){x.fillStyle='#ffbd4a';x.fillText('•',825,ry);x.fillStyle='#c7cdd4';wrapText(x,risk,850,ry,630,26);ry+=76;}x.fillStyle='#727b86';x.font='14px sans-serif';x.fillText(`Inside Airbnb ${market.snapshot} · review-model proxy · evidence confidence ${pct(r.confidence)}`,70,842);x.fillText('Estimated metrics are not a competitor booking ledger. Verify legal permission before contracting.',790,842);c.toBlob(blob=>{const a=document.createElement('a');a.href=URL.createObjectURL(blob);a.download=`${p.code}-minpaku-underwriting.png`;a.click();URL.revokeObjectURL(a.href);},'image/png');}
function wrapText(ctx,text,x,y,maxWidth,lineHeight){const chars=[...text];let line='';let yy=y;for(const ch of chars){const test=line+ch;if(ctx.measureText(test).width>maxWidth&&line){ctx.fillText(line,x,yy);line=ch;yy+=lineHeight;}else line=test;}if(line)ctx.fillText(line,x,yy);}
