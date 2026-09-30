from django.contrib import admin
from .models import Category, Supplier, Product, Staff, Bill, BillItem, ReturnProduct, Purchase, Ledger

admin.site.register(Category)
admin.site.register(Supplier)
admin.site.register(Product)
admin.site.register(Staff)
admin.site.register(Bill)
admin.site.register(BillItem)
admin.site.register(ReturnProduct)
admin.site.register(Purchase)
admin.site.register(Ledger)
