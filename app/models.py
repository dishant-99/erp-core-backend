from sqlalchemy import Boolean, Column, String, Integer, Numeric, TIMESTAMP, Date, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid

from app.db import Base


class StockItem(Base):
    __tablename__ = "stock_items"

    item_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    item_name = Column(String, nullable=False)
    item_qty = Column(Integer, default=0)
    rate = Column(Numeric, nullable=False)
    safety_stock = Column(Integer, default=0)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP,
        server_default=func.now(),
        onupdate=func.now()
    )
class Supplier(Base):
    __tablename__ = "suppliers"

    supplier_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    supplier_name = Column(String, nullable=False)
    supplier_contact = Column(String)
    supplier_email = Column(String)
    supplier_address = Column(String)
    account_balance = Column(Numeric, default=0)
    discount_offered = Column(Numeric, default=0)

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    po_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    supplier_id = Column(UUID(as_uuid=True), ForeignKey("suppliers.supplier_id"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("stock_items.item_id"), nullable=False)

    qty_ordered = Column(Integer, nullable=False)
    final_price_per_item = Column(Numeric)

    po_status = Column(String, default="pending_price_negotiation")

    date_of_order = Column(Date, server_default=func.current_date())

    delivery_inbound_id = Column(UUID(as_uuid=True))

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class Acknowledgement(Base):
    __tablename__ = "acknowledgements"

    ack_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    po_id = Column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.po_id"),
        nullable=False
    )

    final_price_per_item = Column(Numeric, nullable=True)

    # negotiation semantics
    status = Column(String, default="proposed")   # proposed | accepted | rejected | superseded
    is_final = Column(Boolean, default=False)
    version = Column(Integer, default=1)

    created_at = Column(TIMESTAMP, server_default=func.now())

class DeliveryInbound(Base):
    __tablename__ = "delivery_inbound"

    delivery_inbound_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    po_id = Column(UUID(as_uuid=True), ForeignKey("purchase_orders.po_id"), nullable=False)

    expected_date_of_delivery = Column(Date)
    actual_date_of_delivery = Column(Date)

    status = Column(String, default="pending")

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

class Bill(Base):
    __tablename__ = "bills"

    bill_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    po_id = Column(
        UUID(as_uuid=True),
        ForeignKey("purchase_orders.po_id"),
        nullable=False
    )

    ack_id = Column(
        UUID(as_uuid=True),
        ForeignKey("acknowledgements.ack_id"),
        nullable=False
    )

    bill_date = Column(Date, server_default=func.current_date())
    payment_status = Column(String, default="pending")
    payment_reference = Column(String, nullable=True)
    paid_at = Column(TIMESTAMP, nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())


class Client(Base):
    __tablename__ = "clients"

    client_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_name = Column(String, nullable=False)
    client_contact = Column(String)
    client_email = Column(String)
    client_address = Column(String)
    account_balance = Column(Numeric, default=0)
    applicable_discount_rate = Column(Numeric, default=0)


class Quote(Base):
    __tablename__ = "quotes"

    quote_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.client_id"), nullable=False)
    item_id = Column(UUID(as_uuid=True), ForeignKey("stock_items.item_id"), nullable=False)

    order_qty = Column(Integer, nullable=False)
    final_price_per_item = Column(Numeric, nullable=False)

    status = Column(String, default="sent")
    created_at = Column(TIMESTAMP, server_default=func.now())
    version = Column(Integer, default=1)
    is_final = Column(Boolean, default=False)
    superseded_by = Column(UUID(as_uuid=True), nullable=True)



class SalesOrder(Base):
    __tablename__ = "sales_orders"

    so_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.client_id"), nullable=False)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.quote_id"), nullable=True)
    item_id = Column(UUID(as_uuid=True), ForeignKey("stock_items.item_id"), nullable=False)

    qty_ordered = Column(Integer, nullable=False)
    final_price_per_item = Column(Numeric, nullable=False)

    date_of_order = Column(Date, server_default=func.current_date())
    order_status = Column(String, default="pending_price_negotiation")

    invoice_id = Column(UUID(as_uuid=True), nullable=True)
    delivery_outbound_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )


class DeliveryOutbound(Base):
    __tablename__ = "delivery_outbound"

    delivery_outbound_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.so_id"), nullable=False)

    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.invoice_id"), nullable=True)
    date_of_delivery = Column(Date)
    status = Column(String, default="pending")

    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now()
    )
    delivered_qty = Column(Integer, nullable=False)



class Invoice(Base):
    __tablename__ = "invoices"

    invoice_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    so_id = Column(UUID(as_uuid=True), ForeignKey("sales_orders.so_id"), nullable=False)
    quote_id = Column(UUID(as_uuid=True), ForeignKey("quotes.quote_id"), nullable=True)

    invoice_date = Column(Date, server_default=func.current_date())
    payment_status = Column(String, default="pending")

    created_at = Column(TIMESTAMP, server_default=func.now())

    voided = Column(Boolean, default=False)
