from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

class Zone(Base):
    __tablename__='zones'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    name: Mapped[str]=mapped_column(String(80),unique=True,index=True)
    light: Mapped[str|None]=mapped_column(String(40),nullable=True)
    ventilation: Mapped[str|None]=mapped_column(String(40),nullable=True)
    rain_shelter: Mapped[bool]=mapped_column(Boolean,default=False)
    cwa_location: Mapped[str|None]=mapped_column(String(40),nullable=True)

class Seller(Base):
    __tablename__='sellers'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    name: Mapped[str]=mapped_column(String(120),unique=True,index=True)
    seller_type: Mapped[str]=mapped_column(String(30),default='private')
    note: Mapped[str|None]=mapped_column(Text,nullable=True)

class Plant(Base):
    __tablename__='plants'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    name: Mapped[str]=mapped_column(String(120),index=True)
    category: Mapped[str]=mapped_column(String(50),default='other')
    species_code: Mapped[str|None]=mapped_column(String(50),nullable=True)
    rarity: Mapped[str]=mapped_column(String(30),default='common')
    propagation_method: Mapped[str|None]=mapped_column(String(40),nullable=True)
    status: Mapped[str]=mapped_column(String(20),default='alive')
    hp: Mapped[int]=mapped_column(Integer,default=100)
    watering_interval_days: Mapped[int]=mapped_column(Integer,default=3)
    drought_tolerance_days: Mapped[int]=mapped_column(Integer,default=5)
    last_watered_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    purchase_cost: Mapped[float]=mapped_column(Float,default=0)
    market_value: Mapped[float]=mapped_column(Float,default=0)
    amortized_cost: Mapped[float]=mapped_column(Float,default=0)
    propagation_cost: Mapped[float]=mapped_column(Float,default=0)
    sale_price: Mapped[float|None]=mapped_column(Float,nullable=True)
    death_cause: Mapped[str|None]=mapped_column(String(80),nullable=True)
    transfer_to: Mapped[str|None]=mapped_column(String(120),nullable=True)
    transfer_date: Mapped[datetime|None]=mapped_column(DateTime,nullable=True)
    parent_id: Mapped[int|None]=mapped_column(ForeignKey('plants.id'),nullable=True)
    father_id: Mapped[int|None]=mapped_column(ForeignKey('plants.id'),nullable=True)
    zone_id: Mapped[int|None]=mapped_column(ForeignKey('zones.id'),nullable=True)
    seller_id: Mapped[int|None]=mapped_column(ForeignKey('sellers.id'),nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    zone=relationship('Zone')
    seller=relationship('Seller')

class InventoryItem(Base):
    __tablename__='inventory_items'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    kind: Mapped[str]=mapped_column(String(20))
    name: Mapped[str]=mapped_column(String(120),index=True)
    quantity: Mapped[float]=mapped_column(Float,default=0)
    unit: Mapped[str]=mapped_column(String(20),default='pcs')
    unit_cost: Mapped[float]=mapped_column(Float,default=0)
    capacity: Mapped[float|None]=mapped_column(Float,nullable=True)
    remaining: Mapped[float|None]=mapped_column(Float,nullable=True)
    reusable: Mapped[bool]=mapped_column(Boolean,default=False)
    quality_level: Mapped[int]=mapped_column(Integer,default=1)

class FinanceEntry(Base):
    __tablename__='finance_entries'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    entry_type: Mapped[str]=mapped_column(String(30))
    amount: Mapped[float]=mapped_column(Float)
    plant_id: Mapped[int|None]=mapped_column(ForeignKey('plants.id'),nullable=True)
    note: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class PhotoLog(Base):
    __tablename__='photo_logs'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    plant_id: Mapped[int]=mapped_column(ForeignKey('plants.id'))
    angle: Mapped[str]=mapped_column(String(40))
    filename: Mapped[str]=mapped_column(String(255))
    note: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)


class PhotoBlob(Base):
    __tablename__='photo_blobs'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    photo_log_id: Mapped[int]=mapped_column(ForeignKey('photo_logs.id'),unique=True,index=True)
    content_type: Mapped[str]=mapped_column(String(100),default='image/jpeg')
    data_base64: Mapped[str]=mapped_column(Text)

class HarvestLog(Base):
    __tablename__='harvest_logs'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    plant_id: Mapped[int]=mapped_column(ForeignKey('plants.id'))
    amount: Mapped[float]=mapped_column(Float)
    unit: Mapped[str]=mapped_column(String(20),default='g')
    note: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)

class CompostBatch(Base):
    __tablename__='compost_batches'
    id: Mapped[int]=mapped_column(Integer,primary_key=True)
    name: Mapped[str]=mapped_column(String(120))
    compost_type: Mapped[str]=mapped_column(String(20),default='hot')
    carbon_weight: Mapped[float]=mapped_column(Float,default=0)
    nitrogen_weight: Mapped[float]=mapped_column(Float,default=0)
    moisture_pct: Mapped[float]=mapped_column(Float,default=50)
    cn_ratio: Mapped[float]=mapped_column(Float,default=30)
    stage: Mapped[str]=mapped_column(String(30),default='升溫')
    suggestion: Mapped[str|None]=mapped_column(Text,nullable=True)
    created_at: Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
