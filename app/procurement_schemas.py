from pydantic import BaseModel, Field, conint, confloat
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List
from enum import Enum

class BaseSchema(BaseModel):
    model_config = {
        "from_attributes": True
    }

class SupplierCreate(BaseSchema):
    supplier_name: str = Field(..., min_length=2)
    supplier_contact: Optional[str] = None
    supplier_email: Optional[str] = None
    supplier_address: Optional[str] = None
    discount_offered: Optional[confloat(ge=0, le=100)] = 0

class SupplierUpdate(BaseSchema):
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    supplier_email: Optional[str] = None
    supplier_address: Optional[str] = None
    discount_offered: Optional[confloat(ge=0, le=100)] = None

class SupplierResponse(BaseSchema):
    supplier_id: UUID
    supplier_name: str
    supplier_contact: Optional[str]
    supplier_email: Optional[str]
    supplier_address: Optional[str]
    account_balance: float
    discount_offered: float

class POStatus(str, Enum):
    pending_price_negotiation = "pending_price_negotiation"
    approved = "approved"
    acknowledged = "acknowledged"
    received = "received"

class PurchaseOrderCreate(BaseSchema):
    supplier_id: UUID
    item_id: UUID
    qty_ordered: conint(gt=0)
    expected_price_per_item: confloat(gt=0)

class PurchaseOrderUpdate(BaseSchema):
    qty_ordered: Optional[conint(gt=0)] = None
    expected_price_per_item: Optional[confloat(gt=0)] = None

class PurchaseOrderResponse(BaseSchema):
    po_id: UUID
    supplier_id: UUID
    item_id: UUID
    qty_ordered: int
    final_price_per_item: Optional[float]
    po_status: POStatus
    created_at: datetime
    updated_at: datetime

class POApproveResponse(BaseSchema):
    po_id: UUID
    po_status: POStatus
    message: str

class POAcknowledgeRequest(BaseSchema):
    final_price_per_item: Optional[confloat(gt=0)] = None
    action: str = Field(
        ...,
        description="accepted | rejected | revised"
    )

class POAcknowledgeResponse(BaseSchema):
    ack_id: UUID
    po_id: UUID
    final_price_per_item: Optional[float]
    status: str
    is_final: bool
    version: int
    created_at: datetime

class POReceiveRequest(BaseSchema):
    actual_date_of_delivery: date

class POReceiveResponse(BaseSchema):
    po_id: UUID
    delivery_inbound_id: UUID
    new_inventory_qty: int
    message: str

class BillCreateRequest(BaseSchema):
    po_id: UUID

class BillResponse(BaseSchema):
    bill_id: UUID
    po_id: UUID
    ack_id: UUID
    bill_date: date
    payment_reference: str
    payment_status: str
    created_at: datetime

class BillPaymentRequest(BaseSchema):
    payment_reference: str = Field(..., min_length=3)

class BillPaymentResponse(BaseSchema):
    bill_id: UUID
    payment_status: str
    payment_reference: str
    paid_at: datetime

