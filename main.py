import os
import re
from datetime import datetime
from typing import List, Optional, Dict, Any
from bson import ObjectId
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field, validator
from pymongo import MongoClient
import uvicorn
from dotenv import load_dotenv

# load environment variables
load_dotenv()

# MongoDB connection
MONGODB_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "ecommerce_db")

client = MongoClient(MONGODB_URL)
db = client[DATABASE_NAME]

# collections
products_collection = db.products
orders_collection = db.orders

app = FastAPI(
    title="Ecommerce API",
    description="FastAPI backend for ecommerce application",
    version="1.0.0"
)

# Models

class Size(BaseModel):
    size: str
    quantity: int = Field(ge=0)

class Product(BaseModel):
    name: str
    price: float = Field(gt=0)
    sizes: List[Size]

class ProductResponse(BaseModel):
    id: str

class ProductListItem(BaseModel):
    id: str
    name: str
    price: float

class PageInfo(BaseModel):
    next: Optional[int] = None
    limit: int
    previous: Optional[int] = None

class ProductListResponse(BaseModel):
    data: List[ProductListItem]
    page: PageInfo

class OrderItem(BaseModel):
    productid: str
    qty: int = Field(gt=0)

class CreateOrder(BaseModel):
    userId: str
    items: List[OrderItem]

class OrderResponse(BaseModel):
    id: str

class ProductDetails(BaseModel):
    name: str
    id: str

class OrderItemDetail(BaseModel):
    productDetails: ProductDetails
    qty: int

class OrderDetail(BaseModel):
    id: str
    items: List[OrderItemDetail]
    total: float

class OrderListResponse(BaseModel):
    data: List[OrderDetail]
    page: PageInfo

# Helpers

def serialize_object_id(doc: dict) -> dict:
    """Convert MongoDB ObjectId to string"""
    if doc and "_id" in doc:
        doc["id"] = str(doc["_id"])
        del doc["_id"]
    return doc

def create_pagination_info(offset: int, limit: int, total_count: int) -> PageInfo:
    """Create pagination information"""
    next_offset = offset + limit if offset + limit < total_count else None
    previous_offset = max(0, offset - limit) if offset > 0 else None
    
    return PageInfo(
        next=next_offset,
        limit=limit,
        previous=previous_offset if offset > 0 else None
    )

# API Endpoints

@app.post("/products", response_model=ProductResponse, status_code=201)
async def create_product(product: Product):
    """
    Create a new product
    """
    try:
        product_dict = product.dict()
        product_dict["created_at"] = datetime.utcnow()
        
        # Insert product into MongoDB
        result = products_collection.insert_one(product_dict)
        
        return ProductResponse(id=str(result.inserted_id))
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create product: {str(e)}")

@app.get("/products", response_model=ProductListResponse)
async def list_products(
    name: Optional[str] = Query(None, description="Filter by product name (supports regex)"),
    size: Optional[str] = Query(None, description="Filter by available size"),
    limit: int = Query(10, ge=1, le=100, description="Number of products to return"),
    offset: int = Query(0, ge=0, description="Number of products to skip")
):
    """
    Get list of products with optional filtering and pagination
    """
    try:
        query_filter = {}
        
        # Name filter with regex support
        if name:
            query_filter["name"] = {"$regex": re.escape(name), "$options": "i"}
        
        # Size filter
        if size:
            query_filter["sizes.size"] = size
        
        # total count for pagination
        total_count = products_collection.count_documents(query_filter)
        
        # Execute query with pagination
        cursor = products_collection.find(
            query_filter, 
            {"name": 1, "price": 1} 
        ).sort("_id", 1).skip(offset).limit(limit)
        
        products = []
        for doc in cursor:
            product = serialize_object_id(doc)
            products.append(ProductListItem(**product))
        
        # Create pagination info
        page_info = create_pagination_info(offset, limit, total_count)
        
        return ProductListResponse(data=products, page=page_info)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch products: {str(e)}")

@app.post("/orders", response_model=OrderResponse, status_code=201)
async def create_order(order: CreateOrder):
    """
    Create a new order
    """
    try:
        # Validate products exist and calculate total
        total_amount = 0.0
        validated_items = []
        
        for item in order.items:
            try:
                product_id = ObjectId(item.productid)
            except:
                raise HTTPException(status_code=400, detail=f"Invalid product ID: {item.productid}")
            
            product = products_collection.find_one({"_id": product_id})
            if not product:
                raise HTTPException(status_code=404, detail=f"Product not found: {item.productid}")
            
            item_total = product["price"] * item.qty
            total_amount += item_total
            
            validated_items.append({
                "productid": item.productid,
                "qty": item.qty,
                "price": product["price"],
                "item_total": item_total
            })
        
        # order document
        order_dict = {
            "userId": order.userId,
            "items": validated_items,
            "total": total_amount,
            "status": "created",
            "created_at": datetime.utcnow()
        }
        
        # Insert order into MongoDB
        result = orders_collection.insert_one(order_dict)
        
        return OrderResponse(id=str(result.inserted_id))
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create order: {str(e)}")

@app.get("/orders/{user_id}", response_model=OrderListResponse)
async def get_user_orders(
    user_id: str,
    limit: int = Query(10, ge=1, le=100, description="Number of orders to return"),
    offset: int = Query(0, ge=0, description="Number of orders to skip")
):
    try:
        # aggregation pipeline for joining with products
        pipeline = [
            {"$match": {"userId": user_id}},
            {"$sort": {"_id": 1}},
            {"$skip": offset},
            {"$limit": limit},
            {
                "$lookup": {
                    "from": "products",
                    "let": {"items": "$items"},
                    "pipeline": [
                        {
                            "$match": {
                                "$expr": {
                                    "$in": [
                                        {"$toString": "$_id"}, 
                                        "$$items.productid"
                                    ]
                                }
                            }
                        },
                        {"$project": {"_id": 1, "name": 1}}
                    ],
                    "as": "product_details"
                }
            }
        ]
        
        total_count = orders_collection.count_documents({"userId": user_id})
        
        orders_cursor = orders_collection.aggregate(pipeline)
        
        orders = []
        for order_doc in orders_cursor:
            product_map = {str(p["_id"]): p for p in order_doc["product_details"]}
            
            # Build order items with product details
            order_items = []
            for item in order_doc["items"]:
                product_info = product_map.get(item["productid"])
                if product_info:
                    order_item = OrderItemDetail(
                        productDetails=ProductDetails(
                            name=product_info["name"],
                            id=item["productid"]
                        ),
                        qty=item["qty"]
                    )
                    order_items.append(order_item)
            
            # Create order detail
            order_detail = OrderDetail(
                id=str(order_doc["_id"]),
                items=order_items,
                total=order_doc["total"]
            )
            orders.append(order_detail)
        
        page_info = create_pagination_info(offset, limit, total_count)
        
        return OrderListResponse(data=orders, page=page_info)
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch orders: {str(e)}")

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "message": "Ecommerce API",
        "version": "1.0.0",
        "endpoints": [
            "POST /products - Create product",
            "GET /products - List products",
            "POST /orders - Create order", 
            "GET /orders/{user_id} - Get user orders",
            "GET /health - Health check"
        ]
    }

if __name__ == "__main__":
    # Create indexes for better performance
    try:
        # Index for products collection
        products_collection.create_index([("name", 1)])
        products_collection.create_index([("sizes.size", 1)])
        
        # Index for orders collection
        orders_collection.create_index([("userId", 1)])
        orders_collection.create_index([("created_at", -1)])
        
        print("Database indexes created successfully")
    except Exception as e:
        print(f"Failed to create indexes: {e}")
    
    # Run application
    uvicorn.run(
        "main:app", 
        port=8000, 
        reload=True,
        log_level="info"
    )