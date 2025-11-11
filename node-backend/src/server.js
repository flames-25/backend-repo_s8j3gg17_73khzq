import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';
import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import { PrismaClient } from '@prisma/client';

dotenv.config();
const app = express();
const prisma = new PrismaClient();

// Middleware
app.use(cors({ origin: '*', credentials: true }));
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

const JWT_SECRET = process.env.JWT_SECRET || 'supersecret';

// Helpers
function signToken(payload) {
  return jwt.sign(payload, JWT_SECRET, { expiresIn: '7d' });
}

function auth(requiredRole) {
  return async (req, res, next) => {
    try {
      const header = req.headers.authorization || '';
      const token = header.startsWith('Bearer ') ? header.slice(7) : null;
      if (!token) return res.status(401).json({ message: 'Unauthorized' });
      const decoded = jwt.verify(token, JWT_SECRET);
      req.user = decoded;
      if (requiredRole && decoded.role !== requiredRole) {
        return res.status(403).json({ message: 'Forbidden' });
      }
      next();
    } catch (e) {
      return res.status(401).json({ message: 'Unauthorized' });
    }
  };
}

// Health
app.get('/test', async (req, res) => {
  try {
    await prisma.$queryRaw`SELECT 1`;
    res.json({ ok: true, message: 'Node/Express/Prisma API is running' });
  } catch (e) {
    res.status(500).json({ ok: false, error: e.message });
  }
});

// Auth
app.post('/auth/register', async (req, res) => {
  try {
    const { name, email, password, role } = req.body;
    if (!name || !email || !password) return res.status(400).json({ message: 'Missing fields' });
    const hashed = await bcrypt.hash(password, 10);
    const user = await prisma.user.create({ data: { name, email, password: hashed, role: role === 'ADMIN' ? 'ADMIN' : 'USER' } });
    const token = signToken({ id: user.id, email: user.email, role: user.role });
    res.json({ token, user: { id: user.id, name: user.name, email: user.email, role: user.role } });
  } catch (e) {
    if (e.code === 'P2002') return res.status(409).json({ message: 'Email already in use' });
    res.status(500).json({ message: e.message });
  }
});

app.post('/auth/login', async (req, res) => {
  const { email, password } = req.body;
  if (!email || !password) return res.status(400).json({ message: 'Missing fields' });
  const user = await prisma.user.findUnique({ where: { email } });
  if (!user) return res.status(401).json({ message: 'Invalid credentials' });
  const ok = await bcrypt.compare(password, user.password);
  if (!ok) return res.status(401).json({ message: 'Invalid credentials' });
  const token = signToken({ id: user.id, email: user.email, role: user.role });
  res.json({ token, user: { id: user.id, name: user.name, email: user.email, role: user.role } });
});

app.get('/auth/me', auth(), async (req, res) => {
  const user = await prisma.user.findUnique({ where: { id: req.user.id }, select: { id: true, name: true, email: true, role: true, createdAt: true } });
  res.json(user);
});

// Products
app.get('/products', async (req, res) => {
  const { q, category, min_price, max_price, limit = '50' } = req.query;
  const where = {};
  if (q) where.OR = [
    { name: { contains: q, mode: 'insensitive' } },
    { description: { contains: q, mode: 'insensitive' } }
  ];
  if (category) where.category = category;
  if (min_price || max_price) where.price = {
    gte: min_price ? parseFloat(min_price) : undefined,
    lte: max_price ? parseFloat(max_price) : undefined,
  };
  const products = await prisma.product.findMany({
    where,
    include: { discount: true },
    orderBy: { createdAt: 'desc' },
    take: parseInt(limit)
  });
  res.json(products);
});

app.get('/products/:id', async (req, res) => {
  const product = await prisma.product.findUnique({ where: { id: req.params.id }, include: { discount: true, owner: { select: { id: true, name: true } } } });
  if (!product) return res.status(404).json({ message: 'Not found' });
  res.json(product);
});

app.post('/products', auth('ADMIN'), async (req, res) => {
  try {
    const { name, description, imageUrl, price, marketplaceLink, category, discountId } = req.body;
    const data = { name, description, imageUrl, price: parseFloat(price), marketplaceLink, category, discountId: discountId || null, ownerId: req.user.id };
    const created = await prisma.product.create({ data });
    res.status(201).json(created);
  } catch (e) {
    res.status(400).json({ message: e.message });
  }
});

app.put('/products/:id', auth('ADMIN'), async (req, res) => {
  try {
    const { name, description, imageUrl, price, marketplaceLink, category, discountId } = req.body;
    const data = { name, description, imageUrl, price: price !== undefined ? parseFloat(price) : undefined, marketplaceLink, category, discountId: discountId || null };
    const updated = await prisma.product.update({ where: { id: req.params.id }, data });
    res.json(updated);
  } catch (e) {
    res.status(400).json({ message: e.message });
  }
});

app.delete('/products/:id', auth('ADMIN'), async (req, res) => {
  try {
    await prisma.product.delete({ where: { id: req.params.id } });
    res.json({ ok: true });
  } catch (e) {
    res.status(400).json({ message: e.message });
  }
});

// Discounts (admin)
app.post('/discounts', auth('ADMIN'), async (req, res) => {
  try {
    const { percentage, startDate, endDate, active = true } = req.body;
    const created = await prisma.discount.create({ data: { percentage: parseInt(percentage), startDate: new Date(startDate), endDate: new Date(endDate), active } });
    res.status(201).json(created);
  } catch (e) {
    res.status(400).json({ message: e.message });
  }
});

app.get('/discounts', auth('ADMIN'), async (req, res) => {
  const discounts = await prisma.discount.findMany({ orderBy: { createdAt: 'desc' } });
  res.json(discounts);
});

// Users (admin)
app.get('/users', auth('ADMIN'), async (req, res) => {
  const users = await prisma.user.findMany({ select: { id: true, name: true, email: true, role: true, createdAt: true } });
  res.json(users);
});

app.delete('/users/:id', auth('ADMIN'), async (req, res) => {
  try {
    await prisma.user.delete({ where: { id: req.params.id } });
    res.json({ ok: true });
  } catch (e) {
    res.status(400).json({ message: e.message });
  }
});

const PORT = process.env.PORT || 5000;
app.listen(PORT, () => console.log(`Node API running on port ${PORT}`));
