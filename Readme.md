# FastAPI Ecommerce Backend

A complete ecommerce backend API built with FastAPI and MongoDB, featuring product management and order processing capabilities.

## Features

- **Product Management**: Create and list products with size variants
- **Order Management**: Create orders and retrieve user order history
- **Advanced Filtering**: Search products by name (regex support) and filter by size
- **Pagination**: Efficient pagination for all list endpoints
- **Data Validation**: Comprehensive request/response validation using Pydantic
- **Database Optimization**: Proper indexing and aggregation queries
- **Error Handling**: Robust error handling with meaningful HTTP status codes

## Tech Stack

- **Framework**: FastAPI 0.104.1
- **Database**: MongoDB with PyMongo
- **Validation**: Pydantic v2
- **Server**: Uvicorn ASGI server
- **Python**: 3.10+ compatible

## API Endpoints

### Products

#### Create Product

- **Endpoint**: `POST /products`
- **Status Code**: 201 (CREATED)
- **Request Body**:

```json
{
  "name": "Sample Product",
  "price": 100.0,
  "sizes": [
    {
      "size": "large",
      "quantity": 10
    },
    {
      "size": "medium",
      "quantity": 5
    }
  ]
}
```

- **Response**:

```json
{
  "id": "507f1f77bcf86cd799439011"
}
```

#### List Products

- **Endpoint**: `GET /products`
- **Status Code**: 200 (OK)
- **Query Parameters**:

  - `name` (optional): Filter by product name (supports regex/partial search)
  - `size` (optional): Filter products that have the specified size
  - `limit` (optional, default=10): Number of products to return
  - `offset` (optional, default=0): Number of products to skip for pagination

- **Response**:

```json
{
  "data": [
    {
      "id": "507f1f77bcf86cd799439011",
      "name": "Sample Product",
      "price": 100.0
    }
  ],
  "page": {
    "next": 10,
    "limit": 10,
    "previous": null
  }
}
```

### Orders

#### Create Order

- **Endpoint**: `POST /orders`
- **Status Code**: 201 (CREATED)
- **Request Body**:

```json
{
  "userId": "user_1",
  "items": [
    {
      "productid": "507f1f77bcf86cd799439011",
      "qty": 2
    },
    {
      "productid": "507f1f77bcf86cd799439012",
      "qty": 1
    }
  ]
}
```

- **Response**:

```json
{
  "id": "507f1f77bcf86cd799439013"
}
```

#### Get User Orders

- **Endpoint**: `GET /orders/{user_id}`
- **Status Code**: 200 (OK)
- **Query Parameters**:

  - `limit` (optional, default=10): Number of orders to return
  - `offset` (optional, default=0): Number of orders to skip for pagination

- **Response**:

```json
{
  "data": [
    {
      "id": "507f1f77bcf86cd799439013",
      "items": [
        {
          "productDetails": {
            "name": "Sample Product",
            "id": "507f1f77bcf86cd799439011"
          },
          "qty": 2
        }
      ],
      "total": 200.0
    }
  ],
  "page": {
    "next": 10,
    "limit": 10,
    "previous": null
  }
}
```

## Installation & Setup

### Prerequisites

- Python 3.10 or higher
- MongoDB (local installation or MongoDB Atlas account)

### Local Development Setup

1. **Clone the repository and navigate to the project directory**

2. **Create and activate virtual environment**:

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**:

```bash
pip install -r requirements.txt
```

4. **Set up environment variables**:

```bash
cp .env.example .env
```

Edit `.env` file with your MongoDB configuration:

- For local MongoDB: `MONGODB_URL=mongodb://localhost:27017`
- For MongoDB Atlas: `MONGODB_URL=mongodb+srv://username:password@cluster.mongodb.net/`

5. **Run the application**:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

6. **Access the API**:

- API Base URL: `http://localhost:8000`
- Interactive Docs: `http://localhost:8000/docs`
- Health Check: `http://localhost:8000/health`

### MongoDB Atlas Setup (Free M0 Cluster)

1. Create account at [MongoDB Atlas](https://www.mongodb.com/atlas)
2. Create a new M0 (free) cluster
3. Set up database user credentials
4. Whitelist your IP address (or use 0.0.0.0/0 for development)
5. Get connection string and update `.env` file

## Database Schema

### Products Collection

```json
{
  "_id": ObjectId,
  "name": "string",
  "price": 100.0,
  "sizes": [
    {
      "size": "string",
      "quantity": 0
    }
  ],
  "created_at": ISODate
}
```

### Orders Collection

```json
{
  "_id": ObjectId,
  "userId": "string",
  "items": [
    {
      "productid": "string",
      "qty": 3,
      "price": 100.0,
      "item_total": 300.0
    }
  ],
  "total": 300.0,
  "status": "created",
  "created_at": ISODate
}
```

## Database Optimization

### Indexes

The application automatically creates the following indexes for optimal performance:

**Products Collection**:

- `name`: For name-based filtering and searching
- `sizes.size`: For size-based filtering

**Orders Collection**:

- `userId`: For efficient user order retrieval
- `created_at`: For chronological sorting

### Query Optimization

- Uses MongoDB aggregation pipeline for complex joins
- Implements efficient pagination with skip/limit
- Excludes unnecessary fields in product listings
- Uses projection to reduce data transfer

## Testing the API

### Using curl

**Create a Product**:

```bash
curl -X POST "http://localhost:8000/products" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "iPhone 14",
    "price": 999.99,
    "sizes": [
      {"size": "128GB", "quantity": 10},
      {"size": "256GB", "quantity": 5}
    ]
  }'
```

**List Products**:

```bash
curl "http://localhost:8000/products?limit=5&name=iPhone"
```

**Create an Order**:

```bash
curl -X POST "http://localhost:8000/orders" \
  -H "Content-Type: application/json" \
  -d '{
    "userId": "user_1",
    "items": [
      {"productid": "PRODUCT_ID_HERE", "qty": 1}
    ]
  }'
```

**Get User Orders**:

```bash
curl "http://localhost:8000/orders/user_1?limit=5"
```

## Error Handling

The API includes comprehensive error handling:

- **400 Bad Request**: Invalid input data or malformed requests
- **404 Not Found**: Product or resource not found
- **422 Unprocessable Entity**: Validation errors
- **500 Internal Server Error**: Server-side errors
- **503 Service Unavailable**: Database connection issues

## Project Structure

```
├── main.py              # Main application file
├── requirements.txt     # Python dependencies
├── .env.example        # Environment variables template
├── README.md           # Documentation
└── .env               # Environment variables (create from .env.example)
```

## Development Notes

- The application uses Pydantic v2 for data validation
- All MongoDB ObjectIds are automatically converted to strings in responses
- Pagination information includes next/previous page indicators
- Product listings exclude size information for performance
- Order creation validates product existence and calculates totals
- Database connections are handled automatically by PyMongo

## Production Considerations

For production deployment, consider:

1. **Environment Variables**: Use proper secret management
2. **Database Connection**: Connection pooling and replica sets
3. **Authentication**: Implement JWT or API key authentication
4. **Rate Limiting**: Add request rate limiting
5. **Logging**: Structured logging with correlation IDs
6. **Monitoring**: Health checks and metrics collection
7. **Caching**: Redis for frequently accessed data
8. **Security**: Input sanitization and CORS configuration
