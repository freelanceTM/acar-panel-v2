from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

# User schemas
class UserBase(BaseModel):
    username: str
    email: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(UserBase):
    id: int
    is_dealer: bool
    is_admin: bool
    is_active: bool
    profile_title: str
    announcement: str
    server_name_template: str
    happ_api_key: str
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    profile_title: Optional[str] = None
    announcement: Optional[str] = None
    server_name_template: Optional[str] = None
    happ_api_key: Optional[str] = None

# Unlimited Source schemas
class UnlimitedSourceBase(BaseModel):
    url: str
    name: Optional[str] = "Source"
    is_active: Optional[bool] = True

class UnlimitedSourceCreate(UnlimitedSourceBase):
    pass

class UnlimitedSourceOut(UnlimitedSourceBase):
    id: int
    owner_id: int
    last_fetched_at: Optional[datetime]
    class Config:
        from_attributes = True

# Server Config schemas
class ServerConfigOut(BaseModel):
    id: int
    source_id: int
    protocol: str
    server_name: str
    host: str
    port: int
    priority: int
    is_active: bool
    custom_name: Optional[str]
    class Config:
        from_attributes = True

class ServerConfigUpdate(BaseModel):
    custom_name: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

# Client Key schemas
class ClientKeyBase(BaseModel):
    client_name: Optional[str] = "Client"
    device_limit: Optional[int] = 3
    is_active: Optional[bool] = True
    expires_at: Optional[datetime] = None

class ClientKeyCreate(ClientKeyBase):
    pass

class ClientKeyOut(ClientKeyBase):
    id: int
    dealer_id: int
    token: str
    hwid: str
    created_at: datetime
    class Config:
        from_attributes = True

class ClientKeyReset(BaseModel):
    reset_bindings: Optional[bool] = False
    reset_hwid: Optional[bool] = False

class PaginatedKeys(BaseModel):
    items: List[ClientKeyOut]
    total: int
    page: int
    pages: int
