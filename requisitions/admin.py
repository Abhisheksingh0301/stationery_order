from django.contrib import admin
from .models import Department, Item, FormSubmission, FormSubmissionItem


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display  = ("department_name", "user", "created_at")
    search_fields = ("department_name", "user__username")


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display  = ("item_name", "category", "default_unit", "is_active", "created_at")
    list_filter   = ("is_active", "category")
    search_fields = ("item_name",)


class LineItemInline(admin.TabularInline):
    model = FormSubmissionItem
    extra = 0


@admin.register(FormSubmission)
class FormSubmissionAdmin(admin.ModelAdmin):
    list_display = ("user", "submission_date", "submitted_at", "updated_at")
    list_filter  = ("submission_date",)
    inlines      = [LineItemInline]


admin.site.site_header = "Requisition System Admin"
