import json
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Sum, Count, F, Q, ProtectedError
from django.db.models.functions import TruncDate
from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views.decorators.http import require_POST

from .decorators import admin_required, is_admin
from .forms import (CategoryForm, SupplierForm, ProductForm, PurchaseForm,
                    LedgerForm, StaffForm)
from .models import (Category, Supplier, Product, Staff, Bill, BillItem,
                     ReturnProduct, Purchase, Ledger)


def money(value):
    return Decimal(value).quantize(Decimal('0.01'))


# ---------------------------------------------------------------
# login / logout
# ---------------------------------------------------------------
def home(request):
    if not request.user.is_authenticated:
        return redirect('login')
    if is_admin(request.user):
        return redirect('dashboard')
    return redirect('billing')


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('home')
        messages.error(request, 'Wrong username or password')
    return render(request, 'shop/login.html')


def logout_view(request):
    logout(request)
    return redirect('login')


# ---------------------------------------------------------------
# admin portal - dashboard
# ---------------------------------------------------------------
@admin_required
def dashboard(request):
    today = date.today()
    today_bills = Bill.objects.filter(status='paid', created_at__date=today)
    today_sales = today_bills.aggregate(t=Sum('grand_total'))['t'] or 0
    context = {
        'today_sales': today_sales,
        'today_bill_count': today_bills.count(),
        'product_count': Product.objects.filter(is_active=True).count(),
        'staff_count': Staff.objects.count(),
        'low_stock_count': Product.objects.filter(is_active=True, stock__lte=F('min_stock')).count(),
        'recent_bills': Bill.objects.select_related('user').order_by('-id')[:5],
    }
    return render(request, 'shop/dashboard.html', context)


# ---------------------------------------------------------------
# categories
# ---------------------------------------------------------------
@admin_required
def category_list(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Category added')
            return redirect('category_list')
    else:
        form = CategoryForm()
    categories = Category.objects.annotate(product_count=Count('product')).order_by('name')
    return render(request, 'shop/category_list.html', {'categories': categories, 'form': form})


@admin_required
@require_POST
def category_delete(request, id):
    category = get_object_or_404(Category, id=id)
    try:
        category.delete()
        messages.success(request, 'Category deleted')
    except ProtectedError:
        messages.error(request, 'This category has products, so it cannot be deleted')
    return redirect('category_list')


# ---------------------------------------------------------------
# products
# ---------------------------------------------------------------
@admin_required
def product_list(request):
    products = Product.objects.select_related('category').order_by('name')
    q = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')
    low = request.GET.get('low', '')
    if q:
        products = products.filter(Q(name__icontains=q) | Q(code__icontains=q))
    if category_id:
        products = products.filter(category_id=category_id)
    if low:
        products = products.filter(stock__lte=F('min_stock'))
    context = {
        'products': products,
        'categories': Category.objects.all(),
        'q': q, 'category_id': category_id, 'low': low,
    }
    return render(request, 'shop/product_list.html', context)


@admin_required
def product_add(request):
    form = ProductForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product added')
        return redirect('product_list')
    return render(request, 'shop/form.html', {'form': form, 'title': 'Add Product', 'back': 'product_list'})


@admin_required
def product_edit(request, id):
    product = get_object_or_404(Product, id=id)
    form = ProductForm(request.POST or None, instance=product)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Product updated')
        return redirect('product_list')
    return render(request, 'shop/form.html', {'form': form, 'title': 'Edit Product', 'back': 'product_list'})


@admin_required
@require_POST
def product_delete(request, id):
    product = get_object_or_404(Product, id=id)
    try:
        product.delete()
        messages.success(request, 'Product deleted')
    except ProtectedError:
        # product is used in a bill or purchase, so only hide it
        product.is_active = False
        product.save()
        messages.warning(request, 'Product is used in bills/purchases, so it was marked inactive instead')
    return redirect('product_list')


# ---------------------------------------------------------------
# staff management
# ---------------------------------------------------------------
@admin_required
def staff_list(request):
    staff_members = Staff.objects.select_related('user').order_by('user__username')
    return render(request, 'shop/staff_list.html', {'staff_members': staff_members})


@admin_required
def staff_add(request):
    form = StaffForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        data = form.cleaned_data
        if not data['password']:
            form.add_error('password', 'Password is required for a new staff')
        else:
            user = User.objects.create_user(username=data['username'], password=data['password'],
                                            first_name=data['full_name'], is_active=data['is_active'])
            Staff.objects.create(user=user, phone=data['phone'], role=data['role'])
            messages.success(request, 'Staff added')
            return redirect('staff_list')
    return render(request, 'shop/form.html', {'form': form, 'title': 'Add Staff', 'back': 'staff_list'})


@admin_required
def staff_edit(request, id):
    staff = get_object_or_404(Staff, id=id)
    user = staff.user
    if request.method == 'POST':
        form = StaffForm(request.POST, user_id=user.id)
        if form.is_valid():
            data = form.cleaned_data
            if user == request.user and (not data['is_active'] or data['role'] != 'admin') and not user.is_superuser:
                messages.error(request, 'You cannot remove your own admin access')
                return redirect('staff_list')
            user.username = data['username']
            user.first_name = data['full_name']
            user.is_active = data['is_active']
            if data['password']:
                user.set_password(data['password'])
            user.save()
            staff.phone = data['phone']
            staff.role = data['role']
            staff.save()
            messages.success(request, 'Staff updated')
            return redirect('staff_list')
    else:
        form = StaffForm(user_id=user.id, initial={
            'full_name': user.first_name, 'username': user.username, 'phone': staff.phone,
            'role': staff.role, 'is_active': user.is_active})
    return render(request, 'shop/form.html', {'form': form, 'title': 'Edit Staff', 'back': 'staff_list'})


@admin_required
@require_POST
def staff_delete(request, id):
    staff = get_object_or_404(Staff, id=id)
    user = staff.user
    if user == request.user:
        messages.error(request, 'You cannot delete your own account')
        return redirect('staff_list')
    try:
        user.delete()
        messages.success(request, 'Staff deleted')
    except ProtectedError:
        user.is_active = False
        user.save()
        messages.warning(request, 'This staff has bills, so the account was deactivated instead')
    return redirect('staff_list')


# ---------------------------------------------------------------
# suppliers and purchases
# ---------------------------------------------------------------
@admin_required
def supplier_list(request):
    suppliers = Supplier.objects.annotate(total_purchase=Sum('purchase__total')).order_by('name')
    return render(request, 'shop/supplier_list.html', {'suppliers': suppliers})


@admin_required
def supplier_add(request):
    form = SupplierForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Supplier added')
        return redirect('supplier_list')
    return render(request, 'shop/form.html', {'form': form, 'title': 'Add Supplier', 'back': 'supplier_list'})


@admin_required
def supplier_edit(request, id):
    supplier = get_object_or_404(Supplier, id=id)
    form = SupplierForm(request.POST or None, instance=supplier)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Supplier updated')
        return redirect('supplier_list')
    return render(request, 'shop/form.html', {'form': form, 'title': 'Edit Supplier', 'back': 'supplier_list'})


@admin_required
@require_POST
def supplier_delete(request, id):
    supplier = get_object_or_404(Supplier, id=id)
    try:
        supplier.delete()
        messages.success(request, 'Supplier deleted')
    except ProtectedError:
        messages.error(request, 'This supplier has purchases, so it cannot be deleted')
    return redirect('supplier_list')


@admin_required
def purchase_list(request):
    purchases = Purchase.objects.select_related('supplier', 'product').order_by('-id')[:100]
    return render(request, 'shop/purchase_list.html', {'purchases': purchases})


@admin_required
def purchase_add(request):
    form = PurchaseForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            purchase = form.save(commit=False)
            purchase.total = purchase.quantity * purchase.cost_price
            purchase.save()
            # add the new stock to the product
            product = Product.objects.select_for_update().get(id=purchase.product_id)
            product.stock = product.stock + purchase.quantity
            product.cost_price = purchase.cost_price
            product.save()
            Ledger.objects.create(entry_type='debit', amount=purchase.total,
                                  description='Purchase from ' + purchase.supplier.name + ' - ' + product.name)
        messages.success(request, 'Purchase saved and stock updated')
        return redirect('purchase_list')
    return render(request, 'shop/form.html', {'form': form, 'title': 'Add Purchase (Stock In)', 'back': 'purchase_list'})


# ---------------------------------------------------------------
# bills (admin side)
# ---------------------------------------------------------------
@admin_required
def bill_list(request):
    bills = Bill.objects.select_related('user').order_by('-id')
    q = request.GET.get('q', '').strip()
    from_date = request.GET.get('from', '')
    to_date = request.GET.get('to', '')
    staff_id = request.GET.get('staff', '')
    if q:
        bills = bills.filter(Q(bill_no__icontains=q) | Q(customer_name__icontains=q) | Q(customer_phone__icontains=q))
    if from_date:
        bills = bills.filter(created_at__date__gte=from_date)
    if to_date:
        bills = bills.filter(created_at__date__lte=to_date)
    if staff_id:
        bills = bills.filter(user_id=staff_id)
    context = {'bills': bills[:200], 'q': q, 'from_date': from_date, 'to_date': to_date,
               'staff_id': staff_id, 'users': User.objects.all()}
    return render(request, 'shop/bill_list.html', context)


@admin_required
def bill_detail(request, id):
    bill = get_object_or_404(Bill, id=id)
    returns = ReturnProduct.objects.filter(bill=bill).select_related('product')
    return render(request, 'shop/bill_detail.html', {'bill': bill, 'items': bill.items.select_related('product'),
                                                     'returns': returns})


@admin_required
@require_POST
def bill_cancel(request, id):
    bill = get_object_or_404(Bill, id=id)
    if bill.status == 'cancelled':
        messages.error(request, 'Bill is already cancelled')
    elif ReturnProduct.objects.filter(bill=bill).exists():
        messages.error(request, 'This bill already has returns, so it cannot be cancelled')
    else:
        with transaction.atomic():
            for item in bill.items.all():
                product = Product.objects.select_for_update().get(id=item.product_id)
                product.stock = product.stock + item.quantity
                product.save()
            bill.status = 'cancelled'
            bill.save()
            Ledger.objects.create(entry_type='debit', amount=bill.grand_total,
                                  description='Bill cancelled - ' + bill.bill_no)
        messages.success(request, 'Bill cancelled and stock added back')
    return redirect('bill_detail', id=bill.id)


# ---------------------------------------------------------------
# product returns
# ---------------------------------------------------------------
def already_returned(item):
    return ReturnProduct.objects.filter(bill_item=item).aggregate(t=Sum('quantity'))['t'] or 0


@admin_required
def return_list(request):
    returns = ReturnProduct.objects.select_related('bill', 'product', 'returned_by').order_by('-id')[:200]
    return render(request, 'shop/return_list.html', {'returns': returns})


@admin_required
def return_add(request):
    bill = None
    items = []

    if request.method == 'POST':
        bill = get_object_or_404(Bill, id=request.POST.get('bill_id'), status='paid')
        reason = request.POST.get('reason', '')
        # discount is shared equally on all items when refunding
        discount_ratio = Decimal('0')
        if bill.sub_total > 0:
            discount_ratio = bill.discount / bill.sub_total
        done = 0
        with transaction.atomic():
            for item in bill.items.all():
                try:
                    qty = int(request.POST.get('qty_' + str(item.id)) or 0)
                except ValueError:
                    qty = 0
                if qty <= 0:
                    continue
                if qty > item.quantity - already_returned(item):
                    messages.error(request, 'Too many quantity for ' + item.product.name)
                    continue
                amount = item.price * qty * (1 + item.gst_percent / 100) * (1 - discount_ratio)
                amount = money(amount)
                ReturnProduct.objects.create(bill=bill, bill_item=item, product=item.product, quantity=qty,
                                             refund_amount=amount, reason=reason, returned_by=request.user)
                product = Product.objects.select_for_update().get(id=item.product_id)
                product.stock = product.stock + qty
                product.save()
                Ledger.objects.create(entry_type='debit', amount=amount,
                                      description='Return of ' + product.name + ' - ' + bill.bill_no)
                done += 1
        if done:
            messages.success(request, 'Return saved, stock updated and refund added in ledger')
            return redirect('return_list')
        messages.error(request, 'Enter a quantity for at least one item')
        return redirect('/returns/add/?bill_no=' + bill.bill_no)

    bill_no = request.GET.get('bill_no', '').strip()
    if bill_no:
        bill = Bill.objects.filter(bill_no__iexact=bill_no, status='paid').first()
        if bill is None:
            messages.error(request, 'No paid bill found with this bill number')
        else:
            for item in bill.items.select_related('product'):
                item.can_return = item.quantity - already_returned(item)
                items.append(item)
    return render(request, 'shop/return_add.html', {'bill': bill, 'items': items, 'bill_no': bill_no})


# ---------------------------------------------------------------
# ledger
# ---------------------------------------------------------------
@admin_required
def ledger_list(request):
    entries = Ledger.objects.order_by('-id')
    from_date = request.GET.get('from', '')
    to_date = request.GET.get('to', '')
    entry_type = request.GET.get('type', '')
    if from_date:
        entries = entries.filter(created_at__date__gte=from_date)
    if to_date:
        entries = entries.filter(created_at__date__lte=to_date)
    if entry_type:
        entries = entries.filter(entry_type=entry_type)
    total_credit = entries.filter(entry_type='credit').aggregate(t=Sum('amount'))['t'] or 0
    total_debit = entries.filter(entry_type='debit').aggregate(t=Sum('amount'))['t'] or 0
    context = {'entries': entries[:300], 'total_credit': total_credit, 'total_debit': total_debit,
               'balance': total_credit - total_debit, 'from_date': from_date, 'to_date': to_date,
               'entry_type': entry_type}
    return render(request, 'shop/ledger_list.html', context)


@admin_required
def ledger_add(request):
    form = LedgerForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Ledger entry added')
        return redirect('ledger_list')
    return render(request, 'shop/form.html', {'form': form, 'title': 'Add Ledger Entry', 'back': 'ledger_list'})


# ---------------------------------------------------------------
# reports
# ---------------------------------------------------------------
@admin_required
def reports(request):
    today = date.today()
    from_date = request.GET.get('from') or today.replace(day=1).isoformat()
    to_date = request.GET.get('to') or today.isoformat()

    bills = Bill.objects.filter(status='paid', created_at__date__gte=from_date, created_at__date__lte=to_date)
    sales = bills.aggregate(total=Sum('grand_total'), gst=Sum('gst_amount'), discount=Sum('discount'))
    total_sales = sales['total'] or 0
    total_returns = ReturnProduct.objects.filter(created_at__date__gte=from_date, created_at__date__lte=to_date) \
        .aggregate(t=Sum('refund_amount'))['t'] or 0
    total_purchase = Purchase.objects.filter(created_at__date__gte=from_date, created_at__date__lte=to_date) \
        .aggregate(t=Sum('total'))['t'] or 0

    daily_sales = bills.annotate(day=TruncDate('created_at')).values('day') \
        .annotate(total=Sum('grand_total'), count=Count('id')).order_by('-day')
    staff_sales = bills.values('user__username').annotate(total=Sum('grand_total'), count=Count('id')).order_by('-total')
    payment_sales = bills.values('payment_mode').annotate(total=Sum('grand_total'), count=Count('id'))
    top_products = BillItem.objects.filter(bill__in=bills).values('product__name') \
        .annotate(qty=Sum('quantity'), amount=Sum('total')).order_by('-qty')[:10]
    low_stock = Product.objects.filter(is_active=True, stock__lte=F('min_stock')).order_by('stock')

    context = {
        'from_date': from_date, 'to_date': to_date,
        'total_sales': total_sales, 'total_gst': sales['gst'] or 0, 'total_discount': sales['discount'] or 0,
        'bill_count': bills.count(), 'total_returns': total_returns, 'total_purchase': total_purchase,
        'net_sales': total_sales - total_returns,
        'daily_sales': daily_sales, 'staff_sales': staff_sales, 'payment_sales': payment_sales,
        'top_products': top_products, 'low_stock': low_stock,
    }
    return render(request, 'shop/reports.html', context)


# ---------------------------------------------------------------
# billing portal (staff + admin)
# ---------------------------------------------------------------
@login_required
def billing(request):
    return render(request, 'shop/billing.html')


@login_required
def billing_products(request):
    q = request.GET.get('q', '').strip()
    products = Product.objects.filter(is_active=True, stock__gt=0)
    if q:
        products = products.filter(Q(name__icontains=q) | Q(code__icontains=q))
    data = []
    for p in products.order_by('name')[:40]:
        data.append({'id': p.id, 'name': p.name, 'code': p.code, 'size': p.size, 'color': p.color,
                     'price': float(p.price), 'gst': float(p.gst_percent), 'stock': p.stock})
    return JsonResponse({'products': data})


@login_required
@require_POST
def save_bill(request):
    try:
        data = json.loads(request.body)
        cart = data.get('items', [])
        payment_mode = data.get('payment_mode', 'cash')
        if len(cart) == 0:
            return JsonResponse({'error': 'Cart is empty'}, status=400)
        if payment_mode not in ('cash', 'card', 'upi'):
            return JsonResponse({'error': 'Wrong payment mode'}, status=400)

        with transaction.atomic():
            bill = Bill.objects.create(user=request.user, payment_mode=payment_mode,
                                       customer_name=str(data.get('customer_name', ''))[:100],
                                       customer_phone=str(data.get('customer_phone', ''))[:15])
            sub_total = Decimal('0')
            gst_raw = Decimal('0')

            for c in cart:
                qty = int(c.get('qty', 0))
                # lock the product row so two staff cannot sell the same last piece
                product = Product.objects.select_for_update().get(id=c.get('id'), is_active=True)
                if qty < 1:
                    raise ValueError('Quantity must be at least 1')
                if qty > product.stock:
                    raise ValueError('Not enough stock for ' + product.name + ' (only ' + str(product.stock) + ' left)')
                line_total = product.price * qty
                BillItem.objects.create(bill=bill, product=product, quantity=qty, price=product.price,
                                        gst_percent=product.gst_percent, total=line_total)
                product.stock = product.stock - qty
                product.save()
                sub_total += line_total
                gst_raw += line_total * product.gst_percent / 100

            discount = Decimal(str(data.get('discount') or 0))
            if discount < 0 or discount > sub_total:
                raise ValueError('Discount must be between 0 and the bill amount')
            gst_amount = Decimal('0')
            if sub_total > 0:
                gst_amount = gst_raw * (sub_total - discount) / sub_total
            grand_total = money(sub_total - discount + gst_amount)

            received = Decimal(str(data.get('amount_received') or 0))
            if payment_mode == 'cash':
                if received == 0:
                    received = grand_total
                if received < grand_total:
                    raise ValueError('Cash received is less than the bill total')
            else:
                received = grand_total

            bill.bill_no = 'BILL' + str(bill.id).zfill(5)
            bill.sub_total = money(sub_total)
            bill.discount = money(discount)
            bill.gst_amount = money(gst_amount)
            bill.grand_total = grand_total
            bill.amount_received = money(received)
            bill.save()

            Ledger.objects.create(entry_type='credit', amount=grand_total,
                                  description='Sale - ' + bill.bill_no + ' (' + payment_mode + ')')
    except Product.DoesNotExist:
        return JsonResponse({'error': 'A product in the cart is not available any more'}, status=400)
    except (InvalidOperation, TypeError, AttributeError):
        return JsonResponse({'error': 'Some value in the bill is not valid'}, status=400)
    except ValueError as e:
        message = str(e)
        if 'invalid literal' in message:
            message = 'Some value in the bill is not valid'
        return JsonResponse({'error': message}, status=400)

    return JsonResponse({'ok': True, 'bill_id': bill.id, 'bill_no': bill.bill_no,
                         'print_url': '/bills/' + str(bill.id) + '/print/'})


@login_required
def my_bills(request):
    bills = Bill.objects.filter(user=request.user).order_by('-id')
    today_total = bills.filter(status='paid', created_at__date=date.today()).aggregate(t=Sum('grand_total'))['t'] or 0
    return render(request, 'shop/my_bills.html', {'bills': bills[:50], 'today_total': today_total})


@login_required
def bill_print(request, id):
    bill = get_object_or_404(Bill, id=id)
    # staff can only open their own bills
    if not is_admin(request.user) and bill.user != request.user:
        messages.error(request, 'You can only open your own bills')
        return redirect('billing')
    context = {
        'bill': bill, 'items': bill.items.select_related('product'),
        'shop_name': settings.SHOP_NAME, 'shop_address': settings.SHOP_ADDRESS,
        'shop_phone': settings.SHOP_PHONE, 'shop_gstin': settings.SHOP_GSTIN,
        'change': bill.amount_received - bill.grand_total,
    }
    return render(request, 'shop/bill_print.html', context)
