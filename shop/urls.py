from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # admin portal
    path('dashboard/', views.dashboard, name='dashboard'),

    path('categories/', views.category_list, name='category_list'),
    path('categories/delete/<int:id>/', views.category_delete, name='category_delete'),

    path('products/', views.product_list, name='product_list'),
    path('products/add/', views.product_add, name='product_add'),
    path('products/edit/<int:id>/', views.product_edit, name='product_edit'),
    path('products/delete/<int:id>/', views.product_delete, name='product_delete'),

    path('staff/', views.staff_list, name='staff_list'),
    path('staff/add/', views.staff_add, name='staff_add'),
    path('staff/edit/<int:id>/', views.staff_edit, name='staff_edit'),
    path('staff/delete/<int:id>/', views.staff_delete, name='staff_delete'),

    path('suppliers/', views.supplier_list, name='supplier_list'),
    path('suppliers/add/', views.supplier_add, name='supplier_add'),
    path('suppliers/edit/<int:id>/', views.supplier_edit, name='supplier_edit'),
    path('suppliers/delete/<int:id>/', views.supplier_delete, name='supplier_delete'),

    path('purchases/', views.purchase_list, name='purchase_list'),
    path('purchases/add/', views.purchase_add, name='purchase_add'),

    path('bills/', views.bill_list, name='bill_list'),
    path('bills/<int:id>/', views.bill_detail, name='bill_detail'),
    path('bills/<int:id>/print/', views.bill_print, name='bill_print'),
    path('bills/<int:id>/cancel/', views.bill_cancel, name='bill_cancel'),

    path('returns/', views.return_list, name='return_list'),
    path('returns/add/', views.return_add, name='return_add'),

    path('ledger/', views.ledger_list, name='ledger_list'),
    path('ledger/add/', views.ledger_add, name='ledger_add'),
    path('reports/', views.reports, name='reports'),

    # billing portal
    path('billing/', views.billing, name='billing'),
    path('billing/products/', views.billing_products, name='billing_products'),
    path('billing/save/', views.save_bill, name='save_bill'),
    path('my-bills/', views.my_bills, name='my_bills'),
]
