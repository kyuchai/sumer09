import os, json, shutil, urllib.parse, urllib.request, base64
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select
from .db import Base, engine, get_db
from .models import *
from .schemas import *

Base.metadata.create_all(bind=engine)
UPLOAD_DIR=Path(__file__).resolve().parent.parent/'uploads'; UPLOAD_DIR.mkdir(exist_ok=True)

# Load simple backend/.env without requiring an extra package.
_ENV_FILE=Path(__file__).resolve().parent.parent/'.env'
if _ENV_FILE.exists():
    for _line in _ENV_FILE.read_text(encoding='utf-8').splitlines():
        _line=_line.strip()
        if _line and not _line.startswith('#') and '=' in _line:
            _k,_v=_line.split('=',1); os.environ.setdefault(_k.strip(),_v.strip().strip('\"').strip("'"))

app=FastAPI(title='Plantopia API',version='1.1.0',description='Plantopia Final - Local SQLite + Render PostgreSQL ready')
app.add_middleware(CORSMiddleware,allow_origins=['*'],allow_methods=['*'],allow_headers=['*'])
app.mount('/uploads',StaticFiles(directory=str(UPLOAD_DIR)),name='uploads')

NATIVE_SPECIES=[
 ('P01','Platycerium alcicorne'),('P02','Platycerium andinum'),('P03','Platycerium bifurcatum'),('P04','Platycerium coronarium'),
 ('P05','Platycerium elephantotis'),('P06','Platycerium ellisii'),('P07','Platycerium grande'),('P08','Platycerium hillii'),
 ('P09','Platycerium holttumii'),('P10','Platycerium madagascariense'),('P11','Platycerium quadridichotomum'),('P12','Platycerium ridleyi'),
 ('P13','Platycerium stemaria'),('P14','Platycerium superbum'),('P15','Platycerium veitchii'),('P16','Platycerium wallichii'),
 ('P17','Platycerium wandae'),('P18','Platycerium willinckii')]
DEATH_CAUSES=['生理枯死','過濕爛根','真菌細菌病害','蟲害','蛀心蟲','曬傷']

@app.get('/health')
def health(): return {'status':'ok','version':'1.0.0','database':'sqlite' if str(engine.url).startswith('sqlite') else 'external'}

@app.post('/seed')
def seed(db:Session=Depends(get_db)):
    if not db.scalar(select(Zone).limit(1)):
        db.add_all([Zone(name='陽台 A',light='明亮散射光',ventilation='良好',rain_shelter=False,cwa_location='臺中市'),Zone(name='室內層架',light='植物燈',ventilation='一般',rain_shelter=True,cwa_location='臺中市')])
    if not db.scalar(select(InventoryItem).limit(1)):
        db.add_all([InventoryItem(kind='equipment',name='3 吋盆',quantity=20,unit='pcs',unit_cost=20,reusable=True,quality_level=2),InventoryItem(kind='equipment',name='5 吋盆',quantity=10,unit='pcs',unit_cost=40,reusable=True,quality_level=2),InventoryItem(kind='consumable',name='綜合介質',quantity=1,unit='g',unit_cost=.02,capacity=10000,remaining=10000),InventoryItem(kind='consumable',name='緩釋肥',quantity=1,unit='g',unit_cost=.08,capacity=1000,remaining=1000)])
    db.commit(); return {'ok':True}

@app.post('/zones',response_model=ZoneOut,status_code=201)
def create_zone(payload:ZoneCreate,db:Session=Depends(get_db)):
    if db.scalar(select(Zone).where(Zone.name==payload.name)): raise HTTPException(409,'Zone already exists')
    x=Zone(**payload.model_dump());db.add(x);db.commit();db.refresh(x);return x
@app.get('/zones',response_model=list[ZoneOut])
def zones(db:Session=Depends(get_db)): return list(db.scalars(select(Zone).order_by(Zone.name)))

@app.post('/sellers',response_model=SellerOut,status_code=201)
def add_seller(payload:SellerCreate,db:Session=Depends(get_db)):
    s=db.scalar(select(Seller).where(Seller.name==payload.name))
    if s:return s
    s=Seller(**payload.model_dump());db.add(s);db.commit();db.refresh(s);return s
@app.get('/sellers')
def sellers(db:Session=Depends(get_db)):
    ss=list(db.scalars(select(Seller))); plants=list(db.scalars(select(Plant)))
    out=[]
    for s in ss:
        ps=[p for p in plants if p.seller_id==s.id]; total=len(ps); survived=sum(p.status!='dead' for p in ps)
        avg_cost=sum(p.purchase_cost for p in ps)/total if total else 0
        survival=survived/total if total else 0
        avg_days=sum(max(1,(datetime.utcnow()-p.created_at).days) for p in ps)/total if total else 0
        cp=(survival*70)+(min(avg_days/365,1)*20)+(10/(1+avg_cost/1000)) if total else 0
        out.append({'id':s.id,'name':s.name,'seller_type':s.seller_type,'total_plants':total,'survival_rate':round(survival*100,1),'avg_cost':round(avg_cost,1),'avg_survival_days':round(avg_days,1),'cp_score':round(cp,1)})
    return sorted(out,key=lambda x:x['cp_score'],reverse=True)

@app.post('/plants',response_model=PlantOut,status_code=201)
def create_plant(payload:PlantCreate,db:Session=Depends(get_db)):
    data=payload.model_dump(); seller_name=data.pop('seller_name',None)
    if data.get('zone_id') and not db.get(Zone,data['zone_id']): raise HTTPException(404,'Zone not found')
    if seller_name and not data.get('seller_id'):
        s=db.scalar(select(Seller).where(Seller.name==seller_name))
        if not s: s=Seller(name=seller_name);db.add(s);db.flush()
        data['seller_id']=s.id
    if data.get('father_id') or data.get('parent_id'): data['rarity']='hybrid' if data.get('father_id') else data.get('rarity','common')
    p=Plant(**data);db.add(p);db.flush()
    if p.purchase_cost>0:db.add(FinanceEntry(entry_type='purchase',amount=-p.purchase_cost,plant_id=p.id,note=f'購入 {p.name}'))
    db.commit();db.refresh(p);return p
@app.get('/plants',response_model=list[PlantOut])
def list_plants(zone_id:int|None=None,status:str|None=None,db:Session=Depends(get_db)):
    q=select(Plant)
    if zone_id is not None:q=q.where(Plant.zone_id==zone_id)
    if status:q=q.where(Plant.status==status)
    return list(db.scalars(q.order_by(Plant.id.desc())))
@app.get('/plants/{plant_id}',response_model=PlantOut)
def get_plant(plant_id:int,db:Session=Depends(get_db)):
    p=db.get(Plant,plant_id)
    if not p:raise HTTPException(404,'Plant not found')
    return p
@app.delete('/plants/{plant_id}',status_code=204)
def delete_plant(plant_id:int,db:Session=Depends(get_db)):
    p=db.get(Plant,plant_id)
    if not p:raise HTTPException(404,'Plant not found')
    if p.status!='alive' or p.purchase_cost>0: raise HTTPException(400,'有財務/死亡履歷的植栽不可直接刪除，請使用售出/贈與/死亡結算')
    db.delete(p);db.commit()


def cwa_forecast(location:str|None):
    key=os.getenv('CWA_API_KEY','').strip()
    if not key or not location:return {'enabled':False,'rain_expected':False,'max_pop':None,'message':'未設定 CWA_API_KEY 或場域縣市'}
    try:
        params=urllib.parse.urlencode({'Authorization':key,'format':'JSON','locationName':location})
        url='https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001?'+params
        with urllib.request.urlopen(url,timeout=8) as r:data=json.load(r)
        locs=data.get('records',{}).get('location',[])
        pops=[]
        if locs:
            for e in locs[0].get('weatherElement',[]):
                if e.get('elementName')=='PoP':
                    for t in e.get('time',[]):
                        try:pops.append(float(t.get('parameter',{}).get('parameterName',0)))
                        except:pass
        m=max(pops) if pops else 0
        return {'enabled':True,'rain_expected':m>=50,'max_pop':m,'message':f'{location} 最高降雨機率 {m:.0f}%'}
    except Exception as e:return {'enabled':False,'rain_expected':False,'max_pop':None,'message':f'氣象 API 暫時不可用：{type(e).__name__}'}

@app.get('/weather')
def weather(location:str|None=None):return cwa_forecast(location)
@app.post('/plants/{plant_id}/water',response_model=PlantOut)
def water(plant_id:int,db:Session=Depends(get_db)):
    p=db.get(Plant,plant_id)
    if not p:raise HTTPException(404,'Plant not found')
    if p.status!='alive':raise HTTPException(400,'Only living plants can be watered')
    p.last_watered_at=datetime.utcnow();db.commit();db.refresh(p);return p
@app.get('/plants/{plant_id}/water-status')
def water_status(plant_id:int,db:Session=Depends(get_db)):
    p=db.get(Plant,plant_id)
    if not p:raise HTTPException(404,'Plant not found')
    interval=p.watering_interval_days; wx={'enabled':False,'rain_expected':False}
    if p.zone and not p.zone.rain_shelter:
        wx=cwa_forecast(p.zone.cwa_location)
        if wx.get('rain_expected'): interval+=1
    elapsed=max(0,(datetime.utcnow()-p.last_watered_at).total_seconds()/86400)
    mp=max(0,round(100*(1-elapsed/max(1,interval))))
    return {'plant_id':p.id,'mp':mp,'needs_water':mp==0,'elapsed_days':round(elapsed,2),'effective_interval_days':interval,'weather':wx}
@app.get('/water-statuses')
def water_statuses(db:Session=Depends(get_db)):
    ps=list(db.scalars(select(Plant).where(Plant.status=='alive')));return [water_status(p.id,db) for p in ps]
@app.get('/emergency-care')
def emergency(db:Session=Depends(get_db)):
    now=datetime.utcnow();rows=[]
    for p in db.scalars(select(Plant).where(Plant.status=='alive')):
        days=max(0,(now-p.last_watered_at).total_seconds()/86400);score=days/max(1,p.drought_tolerance_days)
        rows.append({'id':p.id,'name':p.name,'zone_id':p.zone_id,'days_since_water':round(days,2),'drought_tolerance_days':p.drought_tolerance_days,'urgency':round(score,3)})
    return sorted(rows,key=lambda x:x['urgency'],reverse=True)

@app.post('/plants/{plant_id}/death',response_model=PlantOut)
def death(plant_id:int,payload:DeathRequest,db:Session=Depends(get_db)):
    p=db.get(Plant,plant_id)
    if not p:raise HTTPException(404,'Plant not found')
    if p.status!='alive':raise HTTPException(400,'Plant is not alive')
    p.status='dead';p.death_cause=payload.cause
    loss=p.market_value if p.market_value>0 else p.purchase_cost
    if loss>0:db.add(FinanceEntry(entry_type='loss',amount=-loss,plant_id=p.id,note=payload.cause))
    db.commit();db.refresh(p);return p
@app.post('/plants/{plant_id}/sell')
def sell(plant_id:int,payload:SaleRequest,db:Session=Depends(get_db)):
    p=db.get(Plant,plant_id)
    if not p:raise HTTPException(404,'Plant not found')
    if p.status!='alive':raise HTTPException(400,'Only living plants can be sold')
    p.status='sold';p.sale_price=payload.sale_price
    profit=payload.sale_price-p.purchase_cost-p.amortized_cost-p.propagation_cost
    db.add(FinanceEntry(entry_type='sale',amount=payload.sale_price,plant_id=p.id,note=f'淨利={profit:.2f}'))
    db.commit();return {'plant_id':p.id,'sale_price':payload.sale_price,'net_profit':round(profit,2)}
@app.post('/plants/{plant_id}/transfer')
def transfer(plant_id:int,payload:TransferRequest,db:Session=Depends(get_db)):
    p=db.get(Plant,plant_id)
    if not p or p.status!='alive':raise HTTPException(400,'Plant unavailable')
    p.status='transferred';p.transfer_to=payload.recipient;p.transfer_date=datetime.utcnow();db.commit();return {'ok':True}

@app.get('/native-species')
def natives(db:Session=Depends(get_db)):
    codes={p.species_code for p in db.scalars(select(Plant)) if p.species_code and p.status!='dead'}
    items=[{'code':c,'name':n,'collected':c in codes} for c,n in NATIVE_SPECIES]
    count=sum(x['collected'] for x in items);return {'count':count,'total':18,'percent':round(count/18*100,1),'items':items}
@app.get('/gene-tree/{plant_id}')
def gene_tree(plant_id:int,db:Session=Depends(get_db)):
    if not db.get(Plant,plant_id):raise HTTPException(404,'Plant not found')
    allp=list(db.scalars(select(Plant)))
    def node(pid,seen=None):
        seen=set() if seen is None else seen
        if pid in seen:return {'id':pid,'name':'循環參照','children':[]}
        seen=seen|{pid};p=next(x for x in allp if x.id==pid)
        kids=[x for x in allp if x.parent_id==pid]
        return {'id':p.id,'name':p.name,'rarity':p.rarity,'father_id':p.father_id,'status':p.status,'children':[node(k.id,seen) for k in kids]}
    return node(plant_id)

@app.post('/inventory',response_model=InventoryOut,status_code=201)
def inventory_add(payload:InventoryCreate,db:Session=Depends(get_db)):
    item=db.scalar(select(InventoryItem).where(InventoryItem.kind==payload.kind,InventoryItem.name==payload.name))
    if item:
        item.quantity+=payload.quantity;item.unit_cost=payload.unit_cost
        if payload.remaining is not None:item.remaining=(item.remaining or 0)+payload.remaining
        if payload.capacity is not None:item.capacity=max(item.capacity or 0,payload.capacity)
    else:item=InventoryItem(**payload.model_dump());db.add(item)
    cost=payload.quantity*payload.unit_cost
    if cost:db.add(FinanceEntry(entry_type='inventory',amount=-cost,note=f'補貨 {payload.name}'))
    db.commit();db.refresh(item);return item
@app.get('/inventory',response_model=list[InventoryOut])
def inventory(db:Session=Depends(get_db)):return list(db.scalars(select(InventoryItem).order_by(InventoryItem.kind,InventoryItem.name)))
@app.post('/plants/{plant_id}/repot')
def repot(plant_id:int,payload:RepotRequest,db:Session=Depends(get_db)):
    if not db.get(Plant,plant_id):raise HTTPException(404,'Plant not found')
    new=db.get(InventoryItem,payload.new_pot_item_id)
    if not new or new.kind!='equipment' or new.quantity<1:raise HTTPException(400,'新盆器庫存不足')
    new.quantity-=1
    if payload.old_pot_item_id:
        old=db.get(InventoryItem,payload.old_pot_item_id)
        if not old:raise HTTPException(404,'舊盆器不存在')
        old.quantity+=1
    if payload.medium_item_id and payload.medium_amount:
        med=db.get(InventoryItem,payload.medium_item_id)
        if not med or med.remaining is None or med.remaining<payload.medium_amount:raise HTTPException(400,'介質庫存不足')
        med.remaining-=payload.medium_amount
    db.commit();return {'ok':True}
@app.post('/plants/{plant_id}/propagate',response_model=list[PlantOut])
def propagate(plant_id:int,payload:PropagateRequest,db:Session=Depends(get_db)):
    parent=db.get(Plant,plant_id)
    if not parent:raise HTTPException(404,'Parent not found')
    if payload.pot_item_id:
        pot=db.get(InventoryItem,payload.pot_item_id)
        if not pot or pot.quantity<payload.count:raise HTTPException(400,'盆器不足')
        pot.quantity-=payload.count
    children=[]
    for i in range(payload.count):
        c=Plant(name=payload.child_name or f'{parent.name} 側芽 {i+1}',category=parent.category,species_code=parent.species_code,rarity=parent.rarity,propagation_method='分株',watering_interval_days=parent.watering_interval_days,drought_tolerance_days=parent.drought_tolerance_days,parent_id=parent.id,zone_id=parent.zone_id,propagation_cost=payload.propagation_cost_each)
        db.add(c);children.append(c)
    db.commit();[db.refresh(c) for c in children];return children

@app.post('/plants/{plant_id}/photos',status_code=201)
async def photo_upload(plant_id:int,angle:str=Form(...),note:str=Form(''),file:UploadFile=File(...),db:Session=Depends(get_db)):
    if angle not in ['全景','葉正反面','莖基部','介質']:raise HTTPException(400,'angle must be one of 4 standard angles')
    if not db.get(Plant,plant_id):raise HTTPException(404,'Plant not found')
    raw=await file.read()
    if not raw:raise HTTPException(400,'Empty image')
    if len(raw)>8*1024*1024:raise HTTPException(413,'Image too large (max 8 MB)')
    ext=Path(file.filename or '.jpg').suffix.lower() or '.jpg';name=f'{plant_id}_{datetime.utcnow().strftime("%Y%m%d%H%M%S%f")}{ext}'
    x=PhotoLog(plant_id=plant_id,angle=angle,filename=name,note=note);db.add(x);db.flush()
    db.add(PhotoBlob(photo_log_id=x.id,content_type=file.content_type or 'image/jpeg',data_base64=base64.b64encode(raw).decode('ascii')))
    # Keep a local copy for convenient VS Code development; Render persistence is the DB blob.
    try:(UPLOAD_DIR/name).write_bytes(raw)
    except Exception:pass
    db.commit();db.refresh(x)
    return {'id':x.id,'plant_id':plant_id,'angle':angle,'note':note,'url':f'/photo-files/{x.id}','created_at':x.created_at}

@app.get('/photo-files/{photo_id}')
def photo_file(photo_id:int,db:Session=Depends(get_db)):
    x=db.get(PhotoLog,photo_id)
    if not x:raise HTTPException(404,'Photo not found')
    blob=db.scalar(select(PhotoBlob).where(PhotoBlob.photo_log_id==photo_id))
    if blob:
        return Response(content=base64.b64decode(blob.data_base64),media_type=blob.content_type,headers={'Cache-Control':'public, max-age=3600'})
    local=UPLOAD_DIR/x.filename
    if local.exists():
        return Response(content=local.read_bytes(),media_type='image/jpeg',headers={'Cache-Control':'public, max-age=3600'})
    raise HTTPException(404,'Photo data not found')

@app.get('/plants/{plant_id}/photos')
def photos(plant_id:int,db:Session=Depends(get_db)):
    xs=list(db.scalars(select(PhotoLog).where(PhotoLog.plant_id==plant_id).order_by(PhotoLog.created_at.desc())))
    return [{'id':x.id,'angle':x.angle,'note':x.note,'url':f'/photo-files/{x.id}','created_at':x.created_at} for x in xs]

@app.post('/plants/{plant_id}/harvest')
def harvest(plant_id:int,payload:HarvestCreate,db:Session=Depends(get_db)):
    if not db.get(Plant,plant_id):raise HTTPException(404,'Plant not found')
    x=HarvestLog(plant_id=plant_id,**payload.model_dump());db.add(x);db.commit();return {'ok':True}
@app.get('/harvests')
def harvests(db:Session=Depends(get_db)):
    xs=list(db.scalars(select(HarvestLog).order_by(HarvestLog.created_at.desc())))
    return [{'id':x.id,'plant_id':x.plant_id,'amount':x.amount,'unit':x.unit,'note':x.note,'created_at':x.created_at} for x in xs]

@app.post('/compost')
def compost(payload:CompostCreate,db:Session=Depends(get_db)):
    ratio=payload.carbon_weight/payload.nitrogen_weight
    if ratio<25:s='C/N 偏低：建議補充乾樹葉、木屑等高碳材料。'
    elif ratio>35:s='C/N 偏高：建議補充咖啡渣、果皮等高氮材料。'
    else:s='C/N 比例在常用目標區間，可持續監測溫度與濕度。'
    if payload.moisture_pct<40:s+=' 濕度偏低，建議少量補水。'
    elif payload.moisture_pct>65:s+=' 濕度偏高，建議翻堆並加入乾料。'
    stage='升溫' if payload.compost_type=='hot' else '腐熟'
    x=CompostBatch(**payload.model_dump(),cn_ratio=ratio,stage=stage,suggestion=s);db.add(x);db.commit();db.refresh(x)
    return {'id':x.id,'cn_ratio':round(ratio,1),'stage':stage,'suggestion':s}
@app.get('/compost')
def compost_list(db:Session=Depends(get_db)):
    xs=list(db.scalars(select(CompostBatch).order_by(CompostBatch.created_at.desc())))
    return [{'id':x.id,'name':x.name,'compost_type':x.compost_type,'cn_ratio':round(x.cn_ratio,1),'moisture_pct':x.moisture_pct,'stage':x.stage,'suggestion':x.suggestion,'created_at':x.created_at} for x in xs]

@app.get('/analytics')
def analytics(db:Session=Depends(get_db)):
    ps=list(db.scalars(select(Plant))); es=list(db.scalars(select(FinanceEntry)))
    causes={}
    for p in ps:
        if p.status=='dead':causes[p.death_cause or '未分類']=causes.get(p.death_cause or '未分類',0)+1
    monthly={}
    for e in es:
        k=e.created_at.strftime('%Y-%m');monthly[k]=monthly.get(k,0)+e.amount
    return {'death_causes':[{'name':k,'value':v} for k,v in causes.items()],'finance_monthly':[{'month':k,'net_cashflow':round(v,2)} for k,v in sorted(monthly.items())]}

@app.get('/dashboard',response_model=DashboardOut)
def dashboard(db:Session=Depends(get_db)):
    ps=list(db.scalars(select(Plant)));inv=list(db.scalars(select(InventoryItem)));es=list(db.scalars(select(FinanceEntry)));hs=list(db.scalars(select(HarvestLog)))
    live=[p for p in ps if p.status=='alive'];dead=[p for p in ps if p.status=='dead'];sold=[p for p in ps if p.status=='sold'];trans=[p for p in ps if p.status=='transferred']
    pv=sum(p.market_value for p in live);iv=sum(i.quantity*i.unit_cost for i in inv if i.kind=='equipment')+sum((i.remaining if i.remaining is not None else i.quantity)*i.unit_cost for i in inv if i.kind=='consumable')
    low=[]
    for i in inv:
        if i.kind=='consumable' and i.capacity and i.remaining is not None and i.remaining/i.capacity<.2:low.append({'id':i.id,'name':i.name,'remaining_pct':round(i.remaining/i.capacity*100,1)})
    realized=sum((p.sale_price or 0)-p.purchase_cost-p.amortized_cost-p.propagation_cost for p in sold)
    hg=sum(h.amount*(1000 if h.unit=='kg' else 1 if h.unit=='g' else 0) for h in hs)
    return DashboardOut(living_plants=len(live),dead_plants=len(dead),sold_plants=len(sold),transferred_plants=len(trans),plant_market_value=round(pv,2),inventory_value=round(iv,2),total_net_worth=round(pv+iv,2),total_losses=round(-sum(e.amount for e in es if e.entry_type=='loss'),2),total_sales=round(sum(e.amount for e in es if e.entry_type=='sale'),2),total_purchases=round(-sum(e.amount for e in es if e.entry_type in {'purchase','inventory'}),2),realized_profit=round(realized,2),total_harvest_g=round(hg,1),low_stock=low)


# Render production: serve the pre-built React frontend from the same FastAPI service.
FRONTEND_DIST=Path(__file__).resolve().parent.parent.parent/'frontend'/'dist'
if FRONTEND_DIST.exists():
    app.mount('/',StaticFiles(directory=str(FRONTEND_DIST),html=True),name='frontend')
