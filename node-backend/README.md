# Bina Ragam — Node.js/Express + Prisma + PostgreSQL Backend

This is an alternative backend implementation matching the FastAPI features but using the originally requested stack: Node.js, Express, Prisma, and PostgreSQL.

## Features
- JWT auth (register, login, me)
- Role-based access (USER/ADMIN)
- Products CRUD (admin)
- Discounts CRUD (admin)
- Users list/delete (admin)
- Prisma models aligned with the FastAPI shapes

## Quick Start
1. Copy environment file:
   ```bash
   cp .env.example .env
   ```
2. Edit `DATABASE_URL` to your PostgreSQL instance and set `JWT_SECRET`.
3. Install dependencies:
   ```bash
   npm install
   ```
4. Generate Prisma client and run migrations:
   ```bash
   npx prisma generate
   npx prisma migrate dev --name init
   ```
5. Start dev server:
   ```bash
   npm run dev
   ```

## API Endpoints
- Auth
  - POST `/auth/register`
  - POST `/auth/login`
  - GET `/auth/me`
- Products
  - GET `/products`
  - GET `/products/:id`
  - POST `/products` (ADMIN)
  - PUT `/products/:id` (ADMIN)
  - DELETE `/products/:id` (ADMIN)
- Discounts
  - POST `/discounts` (ADMIN)
  - GET `/discounts` (ADMIN)
- Users
  - GET `/users` (ADMIN)
  - DELETE `/users/:id` (ADMIN)
- Health
  - GET `/test`

## Notes
- Passwords are hashed with bcryptjs.
- JWT expiration: 7 days.
- CORS: open for demo; restrict origins in production.
- The data shapes align with the frontend expectations used in this project.
