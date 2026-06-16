from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON, Float, create_engine
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base
import uuid

def generate_uuid():
    return str(uuid.uuid4())

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=True)
    hashed_password = Column(String, nullable=False)
    is_dealer = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Dealer settings
    profile_title = Column(String, default="Premium Subscription")
    announcement = Column(Text, default="")
    server_name_template = Column(String, default="{USERNAME} | Server {NUMBER}")
    happ_api_key = Column(String, default="")
    
    unlimited_sources = relationship("UnlimitedSource", back_populates="owner", cascade="all, delete-orphan")
    client_keys = relationship("ClientKey", back_populates="dealer", cascade="all, delete-orphan")

class UnlimitedSource(Base):
    __tablename__ = "unlimited_sources"
    
    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    url = Column(Text, nullable=False)
    name = Column(String, default="Source")
    is_active = Column(Boolean, default=True)
    last_fetched_at = Column(DateTime(timezone=True), nullable=True)
    cached_config = Column(Text, default="")  # Raw cached config text
    
    owner = relationship("User", back_populates="unlimited_sources")
    servers = relationship("ServerConfig", back_populates="source", cascade="all, delete-orphan")

class ServerConfig(Base):
    __tablename__ = "server_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("unlimited_sources.id"), nullable=False)
    protocol = Column(String, default="vless")  # vless, trojan, vmess
    raw_link = Column(Text, nullable=False)
    server_name = Column(String, default="")
    host = Column(String, default="")
    port = Column(Integer, default=0)
    priority = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    custom_name = Column(String, default="")  # Dealer override
    
    source = relationship("UnlimitedSource", back_populates="servers")

class ClientKey(Base):
    __tablename__ = "client_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    dealer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token = Column(String, unique=True, index=True, default=lambda: generate_uuid().replace("-", "")[:16])
    client_name = Column(String, default="Client")
    device_limit = Column(Integer, default=3)
    hwid = Column(String, default="")  # Happ HWID lock
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    dealer = relationship("User", back_populates="client_keys")
