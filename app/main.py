from fastapi import FastAPI
from app.routes import inventory, procurement, sales

app = FastAPI(title="ERP APIs")

app.include_router(inventory.router)
app.include_router(procurement.router)
app.include_router(sales.router)
