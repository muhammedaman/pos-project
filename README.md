# POS Billing Software (Django + MySQL)

A Point of Sale and Billing web application for a textile / retail shop.
It has an **Admin Portal**, and a **Billing Portal** for staff.

## Technology stack
- Backend: Python 3, Django 4.2
- Database: MySQL
- Frontend: Django templates, Bootstrap 5, a little JavaScript (billing cart)
- Login: Django built-in authentication + role saved in the `staff` table

## Features
**Admin Portal**
- Dashboard (today sales, low stock, recent bills)
- Product CRUD with category, supplier, size, colour, GST %, stock and minimum stock
- Category management
- Staff management (add / edit / disable / delete, admin or staff role)
- Supplier management and Purchases (stock in - increases stock and writes ledger)
- Bills list with filters, bill details, print and cancel bill (stock is added back)
- Product returns (search by bill number, partial returns, stock added back, refund in ledger)
- Ledger (credit / debit, date filter, manual entries)
- Reports (day wise, staff wise, payment mode wise, top products, low stock, GST, returns)

**Billing Portal** (`/billing/`)
- Search product by name or barcode (scanner + Enter works)
- Cart with quantity change, discount, GST calculation
- Cash / Card / UPI payment, cash change calculation
- Bill is saved in one database transaction, and product rows are locked (`select_for_update`)
  so two staff cannot sell the same last piece
- Printable bill (`/bills/<id>/print/`)
- Staff can see only their own bills, and cannot open the admin portal

## Database tables
| Table | Purpose |
|---|---|
| `category` | product categories |
| `supplier` | suppliers |
| `product` | products, price, GST, stock |
| `staff` | extra details + role (admin/staff) for each Django `auth_user` |
| `bill` | one row per bill |
| `bill_item` | products in a bill |
| `return_product` | returned items |
| `purchase` | stock purchases from suppliers |
| `ledger` | all money in (credit) and money out (debit) |

Ledger is filled automatically: sale = credit, purchase = debit, return refund = debit, cancelled bill = debit.

## How to run
1. Install Python 3.8+ and MySQL.
2. Create the database:
   ```sql
   CREATE DATABASE pos_db CHARACTER SET utf8mb4;
   ```
3. Open `pos_project/settings.py` and change the MySQL `USER` and `PASSWORD` in `DATABASES`.
4. Install packages and set up tables:
   ```bash
   python -m venv venv
   venv\Scripts\activate          # Linux/Mac: source venv/bin/activate
   pip install -r requirements.txt
   python manage.py migrate
   python manage.py runserver
   ```
5. Open http://127.0.0.1:8000/

If `mysqlclient` does not install on your computer, use `pip install pymysql` and add these two lines at the
top of `pos_project/__init__.py`:
```python
import pymysql
pymysql.install_as_MySQLdb()
```

## Test credentials
| Role | Username | Password |
|---|---|---|
| Admin | `admin` | `admin123` |
| Staff | `staff1` | `staff123` |
| Staff | `staff2` | `staff123` |

## Important URLs
| Page | URL |
|---|---|
| Login | `/login/` |
| Admin portal | `/dashboard/` |
| Billing portal | `/billing/` |