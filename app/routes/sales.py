from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from uuid import UUID
from sqlalchemy import func
from app.db import SessionLocal
from app.models import Client, Quote, SalesOrder, StockItem, DeliveryOutbound, Invoice
from app.sales_schemas import (
    ClientCreate, ClientResponse,
    QuoteCreate, QuoteResponse,
    SalesOrderCreate, SalesOrderResponse,
    DeliveryOutboundRequest, DeliveryOutboundResponse,
    InvoiceResponse, QuoteReviseRequest
)

router = APIRouter(prefix="/sales", tags=["Sales"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------- CLIENT ----------

@router.post("/clients", response_model=ClientResponse)
def create_client(payload: ClientCreate, db: Session = Depends(get_db)):
    client = Client(**payload.dict())
    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.get("/clients", response_model=list[ClientResponse])
def list_clients(db: Session = Depends(get_db)):
    return db.query(Client).all()


@router.get("/clients/{client_id}", response_model=ClientResponse)
def get_client(client_id: UUID, db: Session = Depends(get_db)):
    client = db.query(Client).filter(Client.client_id == client_id).first()
    if not client:
        raise HTTPException(404, "Client not found")
    return client


# ---------- QUOTES ----------

@router.post("/quotes", response_model=QuoteResponse)
def create_quote(payload: QuoteCreate, db: Session = Depends(get_db)):
    quote = Quote(**payload.dict())
    db.add(quote)
    db.commit()
    db.refresh(quote)
    return quote

@router.post("/quotes/{quote_id}/revise", response_model=QuoteResponse)
def revise_quote(
    quote_id: UUID,
    payload: QuoteReviseRequest,
    db: Session = Depends(get_db)
):
    old = db.query(Quote).filter(Quote.quote_id == quote_id).first()
    if not old:
        raise HTTPException(404, "Quote not found")

    if old.is_final:
        raise HTTPException(400, "Final quote cannot be revised")

    old.status = "superseded"

    new = Quote(
        client_id=old.client_id,
        item_id=old.item_id,
        order_qty=old.order_qty,
        final_price_per_item=payload.revised_price_per_item,
        status="revised",
        version=old.version + 1,
        is_final=False,
        superseded_by=None
    )

    old.superseded_by = new.quote_id

    db.add(new)
    db.commit()
    db.refresh(new)
    return new


@router.post("/quotes/{quote_id}/accept")
def accept_quote(quote_id: UUID, db: Session = Depends(get_db)):
    quote = db.query(Quote).filter(Quote.quote_id == quote_id).first()
    if not quote:
        raise HTTPException(404, "Quote not found")
    if quote.status == "accepted":
        raise HTTPException(400, "Quote already accepted")
    if quote.is_final:
        raise HTTPException(400, "Quote already finalized")

    # reserve inventory
    item = db.query(StockItem).filter(StockItem.item_id == quote.item_id).first()
    if not item or item.item_qty < quote.order_qty:
        raise HTTPException(400, "Insufficient inventory")

    # supersede all other versions
    db.query(Quote).filter(
    Quote.client_id == quote.client_id,
    Quote.item_id == quote.item_id,
    Quote.is_final == False,
    Quote.quote_id != quote.quote_id).update({"status": "superseded"})
    
    quote.is_final = True
    item.item_qty -= quote.order_qty
    quote.status = "accepted"

    so = SalesOrder(
        client_id=quote.client_id,
        quote_id=quote.quote_id,
        item_id=quote.item_id,
        qty_ordered=quote.order_qty,
        final_price_per_item=quote.final_price_per_item,
        order_status="confirmed"
    )

    db.add(so)
    db.flush()

    invoice = Invoice(so_id=so.so_id, quote_id=quote.quote_id)
    db.add(invoice)
    db.flush()

    so.invoice_id = invoice.invoice_id

    client = db.query(Client).filter(Client.client_id == so.client_id).first()
    client.account_balance += so.qty_ordered * so.final_price_per_item

    db.commit()
    db.refresh(so)

    return {"quote_id": quote.quote_id, "so_id": so.so_id}


# ---------- DIRECT SALES ORDER ----------

@router.post("/orders", response_model=SalesOrderResponse)
def create_sales_order(payload: SalesOrderCreate, db: Session = Depends(get_db)):
    item = db.query(StockItem).filter(StockItem.item_id == payload.item_id).first()
    if not item or item.item_qty < payload.qty_ordered:
        raise HTTPException(400, "Insufficient inventory")

    item.item_qty -= payload.qty_ordered

    so = SalesOrder(
        client_id=payload.client_id,
        item_id=payload.item_id,
        qty_ordered=payload.qty_ordered,
        final_price_per_item=payload.final_price_per_item,
        order_status="confirmed"
    )

    db.add(so)
    db.flush()

    invoice = Invoice(so_id=so.so_id)
    db.add(invoice)
    db.flush()

    so.invoice_id = invoice.invoice_id

    client = db.query(Client).filter(Client.client_id == so.client_id).first()
    client.account_balance += so.qty_ordered * so.final_price_per_item

    db.commit()
    db.refresh(so)
    return so


# ---------- DELIVERY ----------

@router.post("/orders/{so_id}/deliver", response_model=DeliveryOutboundResponse)
def deliver_sales_order(
    so_id: UUID,
    payload: DeliveryOutboundRequest,
    db: Session = Depends(get_db)
):
    so = db.query(SalesOrder).filter(SalesOrder.so_id == so_id).first()
    if not so:
        raise HTTPException(404, "SO not found")

    if so.order_status == "cancelled":
        raise HTTPException(400, "Cancelled order cannot be delivered")

    if so.order_status == "delivered":
        raise HTTPException(400, "Order already fully delivered")

    # 🔢 How much already delivered?
    total_delivered = db.query(
        func.coalesce(func.sum(DeliveryOutbound.delivered_qty), 0)
    ).filter(
        DeliveryOutbound.so_id == so_id
    ).scalar()

    # 🚫 Prevent over-delivery
    if total_delivered + payload.delivered_qty > so.qty_ordered:
        raise HTTPException(
            status_code=400,
            detail="Delivered quantity exceeds ordered quantity"
        )

    # 📦 Create delivery record
    delivery = DeliveryOutbound(
        so_id=so_id,
        delivered_qty=payload.delivered_qty,
        date_of_delivery=payload.date_of_delivery,
        status="delivered"
    )

    # 🔄 Update SO status
    if total_delivered + payload.delivered_qty < so.qty_ordered:
        so.order_status = "partially_delivered"
    else:
        so.order_status = "delivered"

    db.add(delivery)
    db.commit()
    db.refresh(delivery)

    return delivery

@router.post("/orders/{so_id}/cancel")
def cancel_sales_order(so_id: UUID, db: Session = Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.so_id == so_id).first()
    if not so:
        raise HTTPException(404, "SO not found")

    if so.order_status in ["delivered", "partially_delivered"]:
        raise HTTPException(400, "Cannot cancel delivered order")

    item = db.query(StockItem).filter(StockItem.item_id == so.item_id).first()
    item.item_qty += so.qty_ordered  # release reservation

    so.order_status = "cancelled"

    db.commit()
    return {"message": "Sales Order cancelled"}

# ---------- READS ----------

@router.get("/orders", response_model=list[SalesOrderResponse])
def list_sales_orders(db: Session = Depends(get_db)):
    return db.query(SalesOrder).all()


@router.get("/orders/{so_id}", response_model=SalesOrderResponse)
def get_sales_order(so_id: UUID, db: Session = Depends(get_db)):
    so = db.query(SalesOrder).filter(SalesOrder.so_id == so_id).first()
    if not so:
        raise HTTPException(404, "SO not found")
    return so


@router.get("/deliveries", response_model=list[DeliveryOutboundResponse])
def list_deliveries(db: Session = Depends(get_db)):
    return db.query(DeliveryOutbound).all()


@router.get("/invoices", response_model=list[InvoiceResponse])
def list_invoices(db: Session = Depends(get_db)):
    return db.query(Invoice).all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: UUID, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")
    return invoice

@router.post("/invoices/{invoice_id}/void")
def void_invoice(invoice_id: UUID, db: Session = Depends(get_db)):
    invoice = db.query(Invoice).filter(Invoice.invoice_id == invoice_id).first()
    if not invoice:
        raise HTTPException(404, "Invoice not found")

    if invoice.payment_status == "paid":
        raise HTTPException(400, "Paid invoice cannot be voided")

    invoice.voided = True
    invoice.payment_status = "voided"

    db.commit()
    return {"message": "Invoice voided"}
