from typing import Optional, Dict, List
from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, Field, conint, confloat
from enum import Enum

class BaseSchema(BaseModel):
    model_config = {
        "from_attributes": True
    }


class ItemCreate(BaseSchema):
    item_name: str = Field(..., min_length=1, description="Name of the inventory item")
    item_qty: conint(ge=0) = Field(..., description="Initial quantity")
    rate: confloat(gt=0) = Field(..., description="Unit rate")
    safety_stock: Optional[conint(ge=0)] = Field(
        default=0, description="Safety stock threshold"
    )
    attributes: Optional[Dict[str, str]] = Field(
        default=None, description="Flexible item metadata"
    )

class ItemUpdate(BaseSchema):
    item_name: Optional[str] = Field(None, min_length=1)
    rate: Optional[confloat(gt=0)] = None
    safety_stock: Optional[conint(ge=0)] = None
    attributes: Optional[Dict[str, str]] = None


class ItemResponse(BaseSchema):
    item_id: UUID
    item_name: str
    item_qty: int
    rate: float
    safety_stock: int
    created_at: datetime
    updated_at: datetime


class ItemDetailResponse(BaseSchema):
    item_id: UUID
    item_name: str
    item_qty: int
    rate: float
    safety_stock: int

    below_safety_stock: bool
    buffer_remaining: int
    suggested_reorder_qty: int

    has_inbound: bool
    has_outbound: bool

    created_at: datetime
    updated_at: datetime


class ItemListResponse(BaseSchema):
    item_id: UUID
    item_name: str
    item_qty: int
    rate: float
    safety_stock: int
    below_safety_stock: bool
    suggested_reorder_qty: int
    has_inbound: bool
    has_outbound: bool


class AdjustmentType(str, Enum):
    increase = "increase"
    decrease = "decrease"


class StockAdjustmentCreate(BaseSchema):
    adjustment_type: AdjustmentType
    quantity: conint(gt=0)
    reason: str = Field(..., min_length=3, description="Reason for adjustment")
    note: Optional[str] = None

class StockAdjustmentResponse(BaseSchema):
    item_id: UUID
    new_item_qty: int
    message: str

class LowStockAlertResponse(BaseSchema):
    item_id: UUID
    item_name: str
    current_qty: int
    safety_stock: int
    suggested_reorder_qty: int
    urgency_score: float