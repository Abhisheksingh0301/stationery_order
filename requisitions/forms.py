from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import User
from .models import FormSubmissionItem, Item, Department

_input_cls = "w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
_select_cls = "w-full border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"


class StyledAuthForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({"class": _input_cls, "placeholder": "Username"})
        self.fields["password"].widget.attrs.update({"class": _input_cls, "placeholder": "Password"})


class LineItemForm(forms.Form):
    item_id  = forms.IntegerField(widget=forms.HiddenInput())
    unit     = forms.ChoiceField(
        choices=FormSubmissionItem.UNIT_CHOICES,
        widget=forms.Select(attrs={"class": "border border-gray-300 rounded-md px-2 py-1 w-full"}),
        required=False,
    )
    quantity = forms.DecimalField(
        max_digits=10, decimal_places=2, min_value=0, required=False,
        widget=forms.NumberInput(attrs={
            "class": "border border-gray-300 rounded-md px-2 py-1 w-full",
            "step": "0.01", "min": "0", "placeholder": "0",
        }),
    )


class DepartmentMasterForm(forms.Form):
    department_name = forms.CharField(
        max_length=120,
        widget=forms.TextInput(attrs={"class": _input_cls, "placeholder": "e.g. Finance"}),
    )
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": _input_cls, "placeholder": "Login username"}),
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={"class": _input_cls, "placeholder": "Leave blank to keep existing"}),
    )
    is_active = forms.BooleanField(required=False, initial=True)

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        if instance:
            self.fields["department_name"].initial = instance.department_name
            self.fields["username"].initial = instance.user.username
            self.fields["is_active"].initial = instance.user.is_active

    def clean_department_name(self):
        name = self.cleaned_data["department_name"].strip()
        qs = Department.objects.filter(department_name__iexact=name)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("A department with this name already exists.")
        return name

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        qs = User.objects.filter(username__iexact=username)
        if self.instance:
            qs = qs.exclude(pk=self.instance.user.pk)
        if qs.exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        if not self.instance and not cleaned.get("password"):
            self.add_error("password", "Password is required for new departments.")
        return cleaned


class SuperuserSignupForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={"class": _input_cls, "placeholder": "Superuser username"}),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": _input_cls, "placeholder": "Password"}),
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": _input_cls, "placeholder": "Confirm password"}),
    )

    def clean_username(self):
        username = self.cleaned_data["username"].strip()
        if User.objects.filter(username__iexact=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        cleaned = super().clean()
        pw = cleaned.get("password")
        cpw = cleaned.get("confirm_password")
        if pw and cpw and pw != cpw:
            self.add_error("confirm_password", "Passwords do not match.")
        return cleaned


class ItemMasterForm(forms.ModelForm):
    class Meta:
        model = Item
        fields = ["item_name", "category", "default_unit", "is_active"]
        widgets = {
            "item_name":    forms.TextInput(attrs={"class": _input_cls, "placeholder": "e.g. A4 Paper"}),
            "category":     forms.Select(attrs={"class": _select_cls}),
            "default_unit": forms.Select(attrs={"class": _select_cls}),
            "is_active":    forms.CheckboxInput(attrs={"class": "h-4 w-4"}),
        }

    def clean_item_name(self):
        name = self.cleaned_data["item_name"].strip()
        qs = Item.objects.filter(item_name__iexact=name)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("An item with this name already exists.")
        return name
