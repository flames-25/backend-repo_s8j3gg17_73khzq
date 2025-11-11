Bina Ragam — Backend API (FastAPI + MongoDB)

Note: This environment is provisioned with FastAPI and MongoDB. The API implements all requested features (auth with JWT, role-based access, CRUD for products, users, and discounts) so you can run and iterate locally right away.

Tech Stack
- FastAPI + Uvicorn
- JWT via python-jose
- Password hashing via passlib/bcrypt
- MongoDB (preconfigured in this environment)

Quick Start
1) Python deps
   - Automatically installed by the workspace when you run the project. If running locally:
     pip install -r requirements.txt

2) Environment variables
   The environment provides these automatically:
   - DATABASE_URL: MongoDB connection string
   - DATABASE_NAME: Target database name
   - Optional: SECRET_KEY (defaults set in code). For production, set your own.

3) Run server
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload

API Overview
Auth
- POST /auth/register
  body: { name, email, password, role?('user'|'admin') }
  returns: user public object
- POST /auth/login (form-encoded: username, password)
  returns: { access_token, token_type }
- GET /auth/me (Bearer token)
  returns: current user public

Products
- GET /products?q=&category=&min_price=&max_price=&limit=
  returns: list of products
- GET /products/{product_id}
- POST /products (admin)
- PUT /products/{product_id} (admin)
- DELETE /products/{product_id} (admin)

Discounts (admin)
- POST /discounts
- GET /discounts

Users (admin)
- GET /users
- DELETE /users/{user_id}

Document shapes
User
- id, name, email, role, created_at

Product
- id, name, description, image_url, price, marketplace_link, category?, discount_id?, created_at

Discount
- id, percentage(0-100), start_date, end_date, active, created_at

Notes
- All times are UTC ISO-8601.
- Authorization header: Authorization: Bearer <token>
- Use /test to verify DB connectivity.
