import os
os.environ['DATABASE_URL']='sqlite:///./test_plantopia.db'
from fastapi.testclient import TestClient
from app.main import app
client=TestClient(app)

def test_health():
    r=client.get('/health'); assert r.status_code==200; assert r.json()['status']=='ok'

def test_core_finance_flow():
    client.post('/seed')
    zones=client.get('/zones').json(); zid=zones[0]['id']
    p=client.post('/plants',json={'name':'Test Fern','category':'fern','purchase_cost':500,'market_value':700,'zone_id':zid})
    assert p.status_code==201
    pid=p.json()['id']
    assert client.post(f'/plants/{pid}/water').status_code==200
    sold=client.post(f'/plants/{pid}/sell',json={'sale_price':900})
    assert sold.status_code==200 and sold.json()['net_profit']==400

def test_propagation_gene_and_inventory():
    client.post('/seed')
    zid=client.get('/zones').json()[0]['id']
    pot=next(x for x in client.get('/inventory').json() if x['kind']=='equipment')
    p=client.post('/plants',json={'name':'Mother','category':'fern','species_code':'P01','zone_id':zid}).json()
    before=pot['quantity']
    r=client.post(f"/plants/{p['id']}/propagate",json={'count':2,'pot_item_id':pot['id'],'propagation_cost_each':10})
    assert r.status_code==200 and len(r.json())==2
    after=next(x for x in client.get('/inventory').json() if x['id']==pot['id'])['quantity']
    assert after==before-2
    tree=client.get(f"/gene-tree/{p['id']}").json(); assert len(tree['children'])>=2
    native=client.get('/native-species').json(); assert native['count']>=1

def test_compost_and_emergency():
    c=client.post('/compost',json={'name':'Batch','compost_type':'hot','carbon_weight':30,'nitrogen_weight':1,'moisture_pct':50})
    assert c.status_code==200 and c.json()['cn_ratio']==30.0
    assert client.get('/emergency-care').status_code==200
