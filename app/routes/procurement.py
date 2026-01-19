from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from uuid import UUID

from app.db import SessionLocal
from app.models import Supplier, PurchaseOrder, Acknowledgement, DeliveryInbound, StockItem, Bill
from app.procurement_schemas import (
    SupplierCreate, SupplierUpdate, SupplierResponse,
    PurchaseOrderCreate, PurchaseOrderUpdate, PurchaseOrderResponse,
    POAcknowledgeRequest, POAcknowledgeResponse,
    POApproveResponse,
    POReceiveRequest, POReceiveResponse, BillCreateRequest, BillResponse,BillPaymentRequest,BillPaymentResponse
)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(prefix="/procurement", tags=["Procurement"])

@router.post("/suppliers", response_model=SupplierResponse)
def create_supplier(payload: SupplierCreate, db: Session = Depends(get_db)):
    supplier = Supplier(**payload.dict())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier

@router.get("/suppliers", response_model=list[SupplierResponse])
def list_suppliers(db: Session = Depends(get_db)):
    return db.query(Supplier).all()

@router.get("/suppliers/{supplier_id}", response_model=SupplierResponse)
def get_supplier(supplier_id: UUID, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(Supplier.supplier_id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier

@router.post("/purchase-orders", response_model=PurchaseOrderResponse)
def create_po(payload: PurchaseOrderCreate, db: Session = Depends(get_db)):
    supplier = db.query(Supplier).filter(
        Supplier.supplier_id == payload.supplier_id
    ).first()

    if not supplier:
        raise HTTPException(status_code=400, detail="Supplier not found")

    item = db.query(StockItem).filter(
        StockItem.item_id == payload.item_id
    ).first()

    if not item:
        raise HTTPException(status_code=400, detail="Stock item not found")

    po = PurchaseOrder(
        supplier_id=payload.supplier_id,
        item_id=payload.item_id,
        qty_ordered=payload.qty_ordered,
        final_price_per_item=payload.expected_price_per_item
    )

    db.add(po)
    db.commit()
    db.refresh(po)

    return po


@router.get("/purchase-orders", response_model=list[PurchaseOrderResponse])
def list_pos(db: Session = Depends(get_db)):
    return db.query(PurchaseOrder).all()

@router.get("/purchase-orders/{po_id}", response_model=PurchaseOrderResponse)
def get_po(po_id: UUID, db: Session = Depends(get_db)):
    po = db.query(PurchaseOrder).filter(PurchaseOrder.po_id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="PO not found")
    return po

@router.post(
    "/purchase-orders/{po_id}/acknowledge",
    response_model=POAcknowledgeResponse
)
def acknowledge_po(
    po_id: UUID,
    payload: POAcknowledgeRequest,
    db: Session = Depends(get_db)
):

    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.po_id == po_id
    ).first()

    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    if po.po_status != "pending_price_negotiation":
        raise HTTPException(
            status_code=400,
            detail="PO cannot be acknowledged in its current state"
        )

    # find latest ACK version
    last_ack = (
        db.query(Acknowledgement)
        .filter(Acknowledgement.po_id == po_id)
        .order_by(Acknowledgement.version.desc())
        .first()
    )

    next_version = 1 if not last_ack else last_ack.version + 1

    # handle buyer decision
    action = payload.action.lower()

    if action not in {"accepted", "rejected", "revised"}:
        raise HTTPException(
            status_code=400,
            detail="Invalid ACK action"
        )

    ack = Acknowledgement(
        po_id=po_id,
        final_price_per_item=payload.final_price_per_item,
        status="proposed",
        version=next_version
    )

    if action == "accepted":
        ack.status = "accepted"
        ack.is_final = True

        # supersede all previous ACKs
        db.query(Acknowledgement).filter(
            Acknowledgement.po_id == po_id,
            Acknowledgement.ack_id != ack.ack_id
        ).update(
            {"status": "superseded", "is_final": False}
        )

        # lock PO price from ACK
        po.final_price_per_item = payload.final_price_per_item
        po.po_status = "acknowledged"

        # create delivery inbound (logistics starts)
        delivery = DeliveryInbound(
            po_id=po_id,
            status="in_transit"
        )
        db.add(delivery)

    elif action == "rejected":
        ack.status = "rejected"

    elif action == "revised":
        ack.status = "proposed"
        # PO remains negotiable

    db.add(ack)
    db.commit()
    db.refresh(ack)

    return ack



@router.post(
    "/purchase-orders/{po_id}/receive",
    response_model=POReceiveResponse
)
def receive_po(po_id: UUID, payload: POReceiveRequest, db: Session = Depends(get_db)):

    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.po_id == po_id
    ).first()

    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    # 🔒 STATE GUARD
    if po.po_status != "acknowledged":
        raise HTTPException(
            status_code=400,
            detail="PO must be acknowledged before receiving goods"
        )

    item = db.query(StockItem).filter(
        StockItem.item_id == po.item_id
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    # 🔒 Prevent double receive
    existing_delivery = db.query(DeliveryInbound).filter(
        DeliveryInbound.po_id == po_id,
        DeliveryInbound.status == "received"
    ).first()

    if existing_delivery:
        raise HTTPException(
            status_code=400,
            detail="Goods already received for this PO"
        )

    # 📦 Record inbound delivery
    delivery = DeliveryInbound(
        po_id=po_id,
        actual_date_of_delivery=payload.actual_date_of_delivery,
        status="received"
    )

    # 📈 Update inventory
    item.item_qty += po.qty_ordered

    # 🔁 Update PO
    po.po_status = "received"

    db.add(delivery)
    db.commit()

    return {
        "po_id": po_id,
        "delivery_inbound_id": delivery.delivery_inbound_id,
        "new_inventory_qty": item.item_qty,
        "message": "Goods received and inventory updated"
    }

@router.post("/bills", response_model=BillResponse)
def create_bill(
    payload: BillCreateRequest,
    db: Session = Depends(get_db)
):
    # 1️⃣ Fetch PO
    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.po_id == payload.po_id
    ).first()

    if not po:
        raise HTTPException(status_code=404, detail="PO not found")

    if po.po_status != "received":
        raise HTTPException(
            status_code=400,
            detail="Bill can only be created after PO is received"
        )

    # 2️⃣ Prevent duplicate bill
    existing_bill = db.query(Bill).filter(
        Bill.po_id == payload.po_id
    ).first()

    if existing_bill:
        raise HTTPException(
            status_code=400,
            detail="Bill already exists for this PO"
        )

    # 3️⃣ Fetch final ACK
    final_ack = db.query(Acknowledgement).filter(
        Acknowledgement.po_id == payload.po_id,
        Acknowledgement.is_final == True
    ).first()

    if not final_ack:
        raise HTTPException(
            status_code=400,
            detail="Final ACK not found for this PO"
        )

    # 4️⃣ Fetch supplier
    supplier = db.query(Supplier).filter(
        Supplier.supplier_id == po.supplier_id
    ).first()

    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    # 5️⃣ Create bill
    bill = Bill(
        po_id=payload.po_id,
        ack_id=final_ack.ack_id,
        payment_status="pending"
    )

    # 6️⃣ Update supplier balance
    bill_amount = po.qty_ordered * final_ack.final_price_per_item
    supplier.account_balance += bill_amount

    db.add(bill)
    db.commit()
    db.refresh(bill)

    return bill

@router.post(
    "/bills/{bill_id}/pay",
    response_model=BillPaymentResponse
)
def pay_bill(
    bill_id: UUID,
    payload: BillPaymentRequest,
    db: Session = Depends(get_db)
):
    bill = db.query(Bill).filter(Bill.bill_id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=404, detail="Bill not found")

    if bill.payment_status == "paid":
        raise HTTPException(status_code=400, detail="Bill already paid")

    po = db.query(PurchaseOrder).filter(
        PurchaseOrder.po_id == bill.po_id
    ).first()

    supplier = db.query(Supplier).filter(
        Supplier.supplier_id == po.supplier_id
    ).first()

    # calculate bill amount again (never trust stored balance math)
    final_ack = db.query(Acknowledgement).filter(
        Acknowledgement.ack_id == bill.ack_id
    ).first()

    bill_amount = po.qty_ordered * final_ack.final_price_per_item

    # update bill
    bill.payment_status = "paid"
    bill.payment_reference = payload.payment_reference
    bill.paid_at = func.now()

    # update supplier balance
    supplier.account_balance -= bill_amount

    db.commit()

    return {
        "bill_id": bill.bill_id,
        "payment_status": bill.payment_status,
        "payment_reference": bill.payment_reference,
        "paid_at": bill.paid_at
    }
@router.get(
    "/suppliers/{supplier_id}/bills",
    response_model=list[BillResponse]
)
def get_supplier_bills(
    supplier_id: UUID,
    db: Session = Depends(get_db)
):
    bills = (
        db.query(Bill)
        .join(PurchaseOrder, Bill.po_id == PurchaseOrder.po_id)
        .filter(PurchaseOrder.supplier_id == supplier_id)
        .order_by(Bill.created_at.desc())
        .all()
    )

    return bills

