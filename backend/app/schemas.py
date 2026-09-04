from datetime import datetime
from pydantic import BaseModel, Field

class ZoneCreate(BaseModel):
    name:str; light:str|None=None; ventilation:str|None=None; rain_shelter:bool=False; cwa_location:str|None=None
class ZoneOut(ZoneCreate):
    id:int; model_config={'from_attributes':True}

class SellerCreate(BaseModel):
    name:str; seller_type:str='private'; note:str|None=None
class SellerOut(SellerCreate):
    id:int; model_config={'from_attributes':True}

class PlantCreate(BaseModel):
    name:str; category:str='other'; species_code:str|None=None; rarity:str='common'; propagation_method:str|None=None
    watering_interval_days:int=Field(3,ge=1); drought_tolerance_days:int=Field(5,ge=1)
    purchase_cost:float=Field(0,ge=0); market_value:float=Field(0,ge=0)
    zone_id:int|None=None; parent_id:int|None=None; father_id:int|None=None; seller_id:int|None=None; seller_name:str|None=None
class PlantOut(BaseModel):
    id:int; name:str; category:str; species_code:str|None; rarity:str; propagation_method:str|None; status:str; hp:int
    watering_interval_days:int; drought_tolerance_days:int; last_watered_at:datetime; purchase_cost:float; market_value:float
    amortized_cost:float; propagation_cost:float; sale_price:float|None; death_cause:str|None; transfer_to:str|None; transfer_date:datetime|None
    parent_id:int|None; father_id:int|None; zone_id:int|None; seller_id:int|None; created_at:datetime
    model_config={'from_attributes':True}

class InventoryCreate(BaseModel):
    kind:str; name:str; quantity:float=Field(gt=0); unit:str='pcs'; unit_cost:float=Field(ge=0)
    capacity:float|None=Field(default=None,gt=0); remaining:float|None=Field(default=None,ge=0); reusable:bool=False; quality_level:int=Field(1,ge=1,le=5)
class InventoryOut(InventoryCreate):
    id:int; model_config={'from_attributes':True}
class DeathRequest(BaseModel): cause:str
class SaleRequest(BaseModel): sale_price:float=Field(gt=0)
class TransferRequest(BaseModel): recipient:str; note:str|None=None
class RepotRequest(BaseModel):
    new_pot_item_id:int; medium_item_id:int|None=None; medium_amount:float=Field(default=0,ge=0); old_pot_item_id:int|None=None
class PropagateRequest(BaseModel):
    count:int=Field(ge=1,le=100); child_name:str|None=None; pot_item_id:int|None=None; propagation_cost_each:float=Field(default=0,ge=0)
class HarvestCreate(BaseModel): amount:float=Field(gt=0); unit:str='g'; note:str|None=None
class CompostCreate(BaseModel):
    name:str; compost_type:str='hot'; carbon_weight:float=Field(ge=0); nitrogen_weight:float=Field(gt=0); moisture_pct:float=Field(50,ge=0,le=100)
class DashboardOut(BaseModel):
    living_plants:int; dead_plants:int; sold_plants:int; transferred_plants:int; plant_market_value:float; inventory_value:float; total_net_worth:float
    total_losses:float; total_sales:float; total_purchases:float; realized_profit:float; total_harvest_g:float; low_stock:list[dict]
