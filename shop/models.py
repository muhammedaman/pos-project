from django.db import models
from django.contrib.auth.models import User


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'category'


class Supplier(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=15)
    address = models.CharField(max_length=200, blank=True)
    gst_number = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'supplier'


class Product(models.Model):
    name = models.CharField(max_length=150)
    code = models.CharField(max_length=30, unique=True)   # barcode / product code
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, blank=True)
    size = models.CharField(max_length=20, blank=True)
    color = models.CharField(max_length=30, blank=True)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=4, decimal_places=1, default=5)
    stock = models.IntegerField(default=0)
    min_stock = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'product'


class Staff(models.Model):
    ROLE_CHOICES = (('admin', 'Admin'), ('staff', 'Staff'))
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone = models.CharField(max_length=15, blank=True)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')

    def __str__(self):
        return self.user.username

    class Meta:
        db_table = 'staff'


class Bill(models.Model):
    PAYMENT_CHOICES = (('cash', 'Cash'), ('card', 'Card'), ('upi', 'UPI'))
    STATUS_CHOICES = (('paid', 'Paid'), ('cancelled', 'Cancelled'))

    bill_no = models.CharField(max_length=20, blank=True)
    user = models.ForeignKey(User, on_delete=models.PROTECT)   # staff who made the bill
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=15, blank=True)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_mode = models.CharField(max_length=10, choices=PAYMENT_CHOICES, default='cash')
    amount_received = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='paid')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.bill_no

    class Meta:
        db_table = 'bill'


class BillItem(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    gst_percent = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    total = models.DecimalField(max_digits=10, decimal_places=2)   # price x quantity (without gst)

    class Meta:
        db_table = 'bill_item'


class ReturnProduct(models.Model):
    bill = models.ForeignKey(Bill, on_delete=models.PROTECT)
    bill_item = models.ForeignKey(BillItem, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=200, blank=True)
    returned_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'return_product'


class Purchase(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.IntegerField()
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'purchase'


class Ledger(models.Model):
    TYPE_CHOICES = (('credit', 'Credit (money in)'), ('debit', 'Debit (money out)'))
    entry_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    description = models.CharField(max_length=200)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ledger'
