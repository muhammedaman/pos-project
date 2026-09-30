from django import forms
from django.contrib.auth.models import User
from .models import Category, Supplier, Product, Purchase, Ledger


class BootstrapMixin:
    # adds bootstrap classes to every field
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if isinstance(field.widget, forms.CheckboxInput):
                field.widget.attrs['class'] = 'form-check-input'
            elif isinstance(field.widget, forms.Select):
                field.widget.attrs['class'] = 'form-select'
            else:
                field.widget.attrs['class'] = 'form-control'


class CategoryForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name']


class SupplierForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'phone', 'address', 'gst_number']


class ProductForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Product
        fields = ['name', 'code', 'category', 'supplier', 'size', 'color',
                  'cost_price', 'price', 'gst_percent', 'stock', 'min_stock', 'is_active']


class PurchaseForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'product', 'quantity', 'cost_price']

    def clean_quantity(self):
        qty = self.cleaned_data['quantity']
        if qty < 1:
            raise forms.ValidationError('Quantity must be at least 1')
        return qty


class LedgerForm(BootstrapMixin, forms.ModelForm):
    class Meta:
        model = Ledger
        fields = ['entry_type', 'description', 'amount']


class StaffForm(BootstrapMixin, forms.Form):
    full_name = forms.CharField(max_length=100)
    username = forms.CharField(max_length=50)
    password = forms.CharField(max_length=50, required=False, widget=forms.PasswordInput(render_value=False),
                               help_text='Leave empty while editing to keep the old password')
    phone = forms.CharField(max_length=15, required=False)
    role = forms.ChoiceField(choices=(('staff', 'Staff (billing only)'), ('admin', 'Admin')))
    is_active = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, **kwargs):
        self.user_id = kwargs.pop('user_id', None)
        super().__init__(*args, **kwargs)

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exclude(id=self.user_id).exists():
            raise forms.ValidationError('This username is already taken')
        return username
