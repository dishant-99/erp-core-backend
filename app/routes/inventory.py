from fastapi import APIRouter, HTTPException
from uuid import UUID
from sqlalchemy.orm import Session
from fastapi import Depends
from app.db import SessionLocal
from app.models import StockItem
from app.inventory_schemas import (
    ItemCreate,
    ItemResponse,
    ItemListResponse,
    ItemDetailResponse,
    StockAdjustmentCreate, 
    StockAdjustmentResponse,
    AdjustmentType,
    LowStockAlertResponse
)
from sqlalchemy import func

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"]
)
@router.post("/items", response_model=ItemResponse)
def create_inventory_item(
    item: ItemCreate,
    db: Session = Depends(get_db)
):
    new_item = StockItem(
        item_name=item.item_name,
        item_qty=item.item_qty,
        rate=item.rate,
        safety_stock=item.safety_stock
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)
        
    return new_item

@router.get("/items", response_model=list[ItemListResponse])
def get_inventory_items(db: Session = Depends(get_db)):
    items = db.query(StockItem).all()

    response = []

    for item in items:
        # Core truth
        item_qty = item.item_qty
        safety_stock = item.safety_stock

        # Business logic (derived intelligence)
        below_safety_stock = item_qty < safety_stock
        buffer_remaining = max(item_qty - safety_stock, 0)

        # Placeholder logic (will later be AI-powered)
        suggested_reorder_qty = (safety_stock * 2 if below_safety_stock else 0)

        # For now, we assume inbound/outbound detection is stubbed
        # (will integrate with delivery tables later)
        has_inbound = False
        has_outbound = False

        response.append({
            "item_id": item.item_id,
            "item_name": item.item_name,
            "item_qty": item_qty,
            "rate": float(item.rate),
            "safety_stock": safety_stock,
            "below_safety_stock": below_safety_stock,
            "suggested_reorder_qty": suggested_reorder_qty,
            "has_inbound": has_inbound,
            "has_outbound": has_outbound
        })

    return response

@router.get("/items/{item_id}", response_model=ItemDetailResponse)
def get_inventory_item_detail(
    item_id: UUID,
    db: Session = Depends(get_db)
):
    item = db.query(StockItem).filter(StockItem.item_id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    item_qty = item.item_qty
    safety_stock = item.safety_stock

    below_safety_stock = item_qty < safety_stock
    buffer_remaining = item_qty - safety_stock

    if below_safety_stock:
        suggested_reorder_qty = safety_stock * 2 - item_qty
    else:
        suggested_reorder_qty = 0

    # Stubbed context (future delivery integration)
    has_inbound = False
    has_outbound = False

    return {
        "item_id": item.item_id,
        "item_name": item.item_name,
        "item_qty": item_qty,
        "rate": float(item.rate),
        "safety_stock": safety_stock,

        "below_safety_stock": below_safety_stock,
        "buffer_remaining": buffer_remaining,
        "suggested_reorder_qty": suggested_reorder_qty,

        "has_inbound": has_inbound,
        "has_outbound": has_outbound,

        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }

@router.post(
    "/items/{item_id}/adjust",
    response_model=StockAdjustmentResponse
)
def adjust_inventory_item(
    item_id: UUID,
    adjustment: StockAdjustmentCreate,
    db: Session = Depends(get_db)
):
    # 1️⃣ Fetch item
    item = db.query(StockItem).filter(StockItem.item_id == item_id).first()

    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    current_qty = item.item_qty

    # 2️⃣ Determine delta
    if adjustment.adjustment_type == AdjustmentType.increase:
        delta = adjustment.quantity
    else:  # decrease
        delta = -adjustment.quantity

    new_qty = current_qty + delta

    # 3️⃣ Enforce ERP invariant: no negative stock
    if new_qty < 0:
        raise HTTPException(
            status_code=400,
            detail="Stock adjustment would result in negative inventory"
        )

    # 4️⃣ Apply adjustment
    item.item_qty = new_qty
    db.commit()
    db.refresh(item)

    # 5️⃣ Respond
    return {
        "item_id": item.item_id,
        "new_item_qty": new_qty,
        "message": (
            f"Stock {'increased' if delta > 0 else 'decreased'} "
            f"by {adjustment.quantity}. Reason: {adjustment.reason}"
        )
    }

@router.get(
    "/alerts/low-stock",
    response_model=list[LowStockAlertResponse]
)
def get_low_stock_alerts(db: Session = Depends(get_db)):
    items = db.query(StockItem).all()

    alerts = []

    for item in items:
        if item.item_qty < item.safety_stock:
            suggested_reorder_qty = (item.safety_stock * 2) - item.item_qty

            urgency_score = (
                (item.safety_stock - item.item_qty) / item.safety_stock
            )

            alerts.append({
                "item_id": item.item_id,
                "item_name": item.item_name,
                "current_qty": item.item_qty,
                "safety_stock": item.safety_stock,
                "suggested_reorder_qty": suggested_reorder_qty,
                "urgency_score": round(urgency_score, 2)
            })

    # Optional: highest urgency first
    alerts.sort(key=lambda x: x["urgency_score"], reverse=True)

    return alerts
