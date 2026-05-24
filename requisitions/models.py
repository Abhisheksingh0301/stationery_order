from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone


class Department(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="department")
    department_name = models.CharField(max_length=120, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.department_name


class Item(models.Model):
    CATEGORY_CHOICES = [
        ("stationery",  "Stationery"),
        ("it_supplies", "IT Supplies"),
        ("hygiene",     "Hygiene"),
        ("pantry",      "Pantry"),
        ("misc",        "Miscellaneous"),
    ]

    UNIT_CHOICES = [
        ("pcs",     "pcs"),
        ("rolls",   "rolls"),
        ("kg",      "kg"),
        ("g",       "g"),
        ("litres",  "litres"),
        ("ml",      "ml"),
        ("boxes",   "boxes"),
        ("packets", "packets"),
        ("dozen",   "dozen"),
        ("metres",  "metres"),
    ]

    item_name    = models.CharField(max_length=150, unique=True)
    category     = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default="misc")
    default_unit = models.CharField(max_length=20, choices=UNIT_CHOICES, default="pcs")
    is_active    = models.BooleanField(default=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "item_name"]

    def __str__(self):
        return self.item_name


class FormSubmission(models.Model):
    user            = models.ForeignKey(User, on_delete=models.CASCADE, related_name="submissions")
    submitted_at    = models.DateTimeField(auto_now_add=True)
    updated_at      = models.DateTimeField(auto_now=True)
    submission_date = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ["-submitted_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "submission_date"],
                name="one_submission_per_user_per_day",
            )
        ]

    def __str__(self):
        return f"{self.user.username} — {self.submission_date}"


class FormSubmissionItem(models.Model):
    UNIT_CHOICES = Item.UNIT_CHOICES

    submission = models.ForeignKey(
        FormSubmission, on_delete=models.CASCADE, related_name="line_items"
    )
    item     = models.ForeignKey(Item, on_delete=models.PROTECT)
    unit     = models.CharField(max_length=20, choices=UNIT_CHOICES, default="pcs")
    quantity = models.DecimalField(
        max_digits=10, decimal_places=2,
        validators=[MinValueValidator(0)],
    )

    class Meta:
        unique_together = ("submission", "item")
        ordering = ["item__item_name"]

    def __str__(self):
        return f"{self.item.item_name}: {self.quantity} {self.unit}"
