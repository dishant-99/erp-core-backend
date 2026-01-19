from typing import Optional
from uuid import UUID
from datetime import datetime, date
from pydantic import BaseModel, conint, confloat


class BaseSchema(BaseModel):
    model_config = {"from_attributes": True}


# ---------- CLIENT ----------

class ClientCreate(BaseSchema):
    client_name: str
    client_contact: Optional[str]
    client_email: Optional[str]
    client_address: Optional[str]


class ClientResponse(BaseSchema):
    client_id: UUID
    client_name: str
    account_balance: float


# ---------- QUOTES ----------

class QuoteCreate(BaseSchema):
    client_id: UUID
    item_id: UUID
    order_qty: conint(gt=0)
    final_price_per_item: confloat(gt=0)

class QuoteReviseRequest(BaseSchema):
    revised_price_per_item: confloat(gt=0)


class QuoteResponse(BaseSchema):
    quote_id: UUID
    client_id: UUID
    item_id: UUID
    order_qty: int
    final_price_per_item: float
    status: str
    created_at: datetime
    version: int
    is_final: bool



# ---------- SALES ORDERS ----------

class SalesOrderCreate(BaseSchema):
    client_id: UUID
    item_id: UUID
    qty_ordered: conint(gt=0)
    final_price_per_item: conint(gt=0)


class SalesOrderResponse(BaseSchema):
    so_id: UUID
    client_id: UUID
    quote_id: Optional[UUID]
    item_id: UUID
    qty_ordered: int
    final_price_per_item: float
    order_status: str
    created_at: datetime
    updated_at: datetime


# ---------- DELIVERY ----------

class DeliveryOutboundRequest(BaseSchema):
    date_of_delivery: date
    delivered_qty: conint(gt=0)


class DeliveryOutboundResponse(BaseSchema):
    delivery_outbound_id: UUID
    so_id: UUID
    status: str


# ---------- INVOICE ----------

class InvoiceResponse(BaseSchema):
    invoice_id: UUID
    so_id: UUID
    invoice_date: date
    payment_status: str
