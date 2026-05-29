import csv
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from django.core.paginator import Paginator
from django.http import HttpResponse

from .models import Item, FormSubmission, FormSubmissionItem, Department
from .forms import StyledAuthForm, DepartmentMasterForm, ItemMasterForm, SuperuserSignupForm
from .decorators import department_required


def is_staff(user):
    return user.is_authenticated and user.is_staff


# ---------- Auth ----------

def login_view(request):
    if request.user.is_authenticated:
        if request.user.is_staff:
            return redirect("report_list")
        if hasattr(request.user, "department"):
            return redirect("dashboard")
        # logged in but no department assigned — show error on login page
        messages.error(request, "Your account has no department assigned. Contact an administrator.")
    if request.method == "POST":
        form = StyledAuthForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect("dashboard")
        messages.error(request, "Invalid credentials.")
    else:
        form = StyledAuthForm(request)
    return render(request, "requisitions/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("login")


def superuser_signup(request):
    no_superuser_exists = not User.objects.filter(is_superuser=True).exists()
    requesting_superuser = request.user.is_authenticated and request.user.is_superuser

    if not no_superuser_exists and not requesting_superuser:
        messages.error(request, "Access denied.")
        return redirect("login")

    if request.method == "POST":
        form = SuperuserSignupForm(request.POST)
        if form.is_valid():
            user = User.objects.create_superuser(
                username=form.cleaned_data["username"],
                password=form.cleaned_data["password"],
                email="",
            )
            messages.success(request, f"Superuser '{user.username}' created successfully.")
            return redirect("login")
    else:
        form = SuperuserSignupForm()
    return render(request, "requisitions/signup.html", {"form": form})


# ---------- Dashboard ----------

@login_required
@department_required
def dashboard(request):
    today = timezone.localdate()
    today_submission = FormSubmission.objects.filter(
        user=request.user, submission_date=today
    ).first()

    qs = FormSubmission.objects.filter(user=request.user).order_by("-submission_date")
    paginator = Paginator(qs, 10)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "requisitions/dashboard.html", {
        "today_submission": today_submission,
        "page_obj": page,
        "today": today,
    })


# ---------- History ----------

@login_required
@department_required
def submission_history(request):
    qs = (
        FormSubmission.objects
        .filter(user=request.user)
        .prefetch_related("line_items__item")
        .order_by("-submission_date")
    )
    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "requisitions/history.html", {
        "page_obj": page,
        "dept_name": getattr(request.user, "department", None),
    })


# ---------- Create ----------

@login_required
@department_required
def create_form(request):
    today = timezone.localdate()
    existing = FormSubmission.objects.filter(user=request.user, submission_date=today).first()
    if existing:
        messages.info(request, "You already submitted today. Redirecting to edit.")
        return redirect("edit_form", submission_id=existing.id)

    items = Item.objects.filter(is_active=True)

    if request.method == "POST":
        try:
            with transaction.atomic():
                submission = FormSubmission.objects.create(
                    user=request.user, submission_date=today
                )
                any_line = False
                for item in items:
                    qty_raw = request.POST.get(f"quantity_{item.id}", "").strip()
                    unit = request.POST.get(f"unit_{item.id}", "pcs")
                    if qty_raw == "":
                        continue
                    try:
                        qty = float(qty_raw)
                    except ValueError:
                        raise ValueError(f"Invalid quantity for {item.item_name}")
                    if qty < 0:
                        raise ValueError(f"Quantity must be >= 0 for {item.item_name}")
                    if qty == 0:
                        continue
                    FormSubmissionItem.objects.create(
                        submission=submission, item=item, unit=unit, quantity=qty
                    )
                    any_line = True
                if not any_line:
                    raise ValueError("At least one item must have a quantity.")
            messages.success(request, "Requisition submitted successfully.")
            return redirect("success", submission_id=submission.id)
        except ValueError as e:
            messages.error(request, str(e))

    return render(request, "requisitions/form_create.html", {
        "items": items,
        "units": FormSubmissionItem.UNIT_CHOICES,
    })


# ---------- Edit ----------

@login_required
def edit_form(request, submission_id):
    if request.user.is_staff:
        submission = get_object_or_404(FormSubmission, id=submission_id)
    else:
        if not hasattr(request.user, "department"):
            messages.error(request, "Your account has no department assigned. Contact an administrator.")
            return redirect("login")
        submission = get_object_or_404(FormSubmission, id=submission_id, user=request.user)

    items = Item.objects.filter(is_active=True)
    existing = {li.item_id: li for li in submission.line_items.all()}

    if request.method == "POST":
        try:
            with transaction.atomic():
                submission.line_items.all().delete()
                for item in items:
                    qty_raw = request.POST.get(f"quantity_{item.id}", "").strip()
                    unit = request.POST.get(f"unit_{item.id}", "pcs")
                    if qty_raw == "":
                        continue
                    qty = float(qty_raw)
                    if qty < 0:
                        raise ValueError(f"Negative quantity for {item.item_name}")
                    if qty == 0:
                        continue
                    FormSubmissionItem.objects.create(
                        submission=submission, item=item, unit=unit, quantity=qty
                    )
                submission.save()  # bump updated_at
            messages.success(request, "Submission updated.")
            if request.user.is_staff:
                return redirect("report_list")
            return redirect("success", submission_id=submission.id)
        except ValueError as e:
            messages.error(request, str(e))

    return render(request, "requisitions/form_edit.html", {
        "submission": submission,
        "items": items,
        "existing": existing,
        "units": FormSubmissionItem.UNIT_CHOICES,
    })


# ---------- Success ----------

@login_required
@department_required
def success_view(request, submission_id):
    submission = get_object_or_404(FormSubmission, id=submission_id, user=request.user)
    return render(request, "requisitions/success.html", {"submission": submission})


# ---------- Form Print ----------

@login_required
def form_print(request, submission_id):
    if request.user.is_staff:
        submission = get_object_or_404(
            FormSubmission.objects.prefetch_related("line_items__item"),
            id=submission_id,
        )
    else:
        if not hasattr(request.user, "department"):
            messages.error(request, "Your account has no department assigned. Contact an administrator.")
            return redirect("login")
        submission = get_object_or_404(
            FormSubmission.objects.prefetch_related("line_items__item"),
            id=submission_id,
            user=request.user,
        )
    return render(request, "requisitions/form_print.html", {
        "submission": submission,
        "dept_name": getattr(submission.user, "department", None),
        "printed_at": timezone.now(),
    })


# ---------- Department Master ----------

@login_required
@user_passes_test(is_staff)
def department_list(request):
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "all")

    qs = Department.objects.select_related("user").order_by("department_name")
    if q:
        qs = qs.filter(
            Q(department_name__icontains=q) | Q(user__username__icontains=q)
        )
    if status == "active":
        qs = qs.filter(user__is_active=True)
    elif status == "inactive":
        qs = qs.filter(user__is_active=False)

    paginator = Paginator(qs, 15)
    page = paginator.get_page(request.GET.get("page"))

    stats = {
        "total":    Department.objects.count(),
        "active":   Department.objects.filter(user__is_active=True).count(),
        "inactive": Department.objects.filter(user__is_active=False).count(),
    }

    return render(request, "requisitions/department_list.html", {
        "page_obj": page, "q": q, "status": status, "stats": stats,
    })


@login_required
@user_passes_test(is_staff)
def department_create(request):
    if request.method == "POST":
        form = DepartmentMasterForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                user = User.objects.create_user(
                    username=form.cleaned_data["username"],
                    password=form.cleaned_data["password"],
                )
                user.is_active = form.cleaned_data.get("is_active", True)
                user.save()
                Department.objects.create(
                    user=user,
                    department_name=form.cleaned_data["department_name"],
                )
            messages.success(request, "Department created.")
            return redirect("department_list")
    else:
        form = DepartmentMasterForm()
    return render(request, "requisitions/department_form.html", {
        "form": form, "title": "Add Department",
    })


@login_required
@user_passes_test(is_staff)
def department_edit(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    if request.method == "POST":
        form = DepartmentMasterForm(request.POST, instance=department)
        if form.is_valid():
            with transaction.atomic():
                department.department_name = form.cleaned_data["department_name"]
                department.save()
                user = department.user
                user.username = form.cleaned_data["username"]
                user.is_active = form.cleaned_data.get("is_active", True)
                if form.cleaned_data.get("password"):
                    user.set_password(form.cleaned_data["password"])
                user.save()
            messages.success(request, "Department updated.")
            return redirect("department_list")
    else:
        form = DepartmentMasterForm(instance=department)
    return render(request, "requisitions/department_form.html", {
        "form": form,
        "title": f"Edit {department.department_name}",
        "department": department,
    })


@login_required
@user_passes_test(is_staff)
def department_delete(request, dept_id):
    department = get_object_or_404(Department, id=dept_id)
    if request.method == "POST":
        if department.user.submissions.exists():
            department.user.is_active = False
            department.user.save()
            messages.info(request, "Department deactivated (has historical submissions).")
        else:
            user = department.user
            department.delete()
            user.delete()
            messages.success(request, "Department deleted.")
        return redirect("department_list")
    return render(request, "requisitions/department_confirm_delete.html", {
        "department": department,
    })


# ---------- Item Master ----------

@login_required
@user_passes_test(is_staff)
def item_list(request):
    q        = request.GET.get("q", "").strip()
    category = request.GET.get("category", "all")
    status   = request.GET.get("status", "all")

    qs = Item.objects.all()
    if q:
        qs = qs.filter(item_name__icontains=q)
    if category != "all":
        qs = qs.filter(category=category)
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "retired":
        qs = qs.filter(is_active=False)

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))

    stats = {
        "total":      Item.objects.count(),
        "active":     Item.objects.filter(is_active=True).count(),
        "retired":    Item.objects.filter(is_active=False).count(),
        "categories": Item.objects.values("category").distinct().count(),
    }

    return render(request, "requisitions/item_list.html", {
        "page_obj": page, "q": q, "category": category, "status": status,
        "stats": stats, "category_choices": Item.CATEGORY_CHOICES,
    })


@login_required
@user_passes_test(is_staff)
def item_create(request):
    if request.method == "POST":
        form = ItemMasterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Item added.")
            return redirect("item_list")
    else:
        form = ItemMasterForm()
    return render(request, "requisitions/item_form.html", {"form": form, "title": "Add Item"})


@login_required
@user_passes_test(is_staff)
def item_edit(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if request.method == "POST":
        form = ItemMasterForm(request.POST, instance=item)
        if form.is_valid():
            form.save()
            messages.success(request, "Item updated.")
            return redirect("item_list")
    else:
        form = ItemMasterForm(instance=item)
    return render(request, "requisitions/item_form.html", {
        "form": form, "title": f"Edit {item.item_name}", "item": item,
    })


@login_required
@user_passes_test(is_staff)
def item_delete(request, item_id):
    item = get_object_or_404(Item, id=item_id)
    if request.method == "POST":
        if FormSubmissionItem.objects.filter(item=item).exists():
            item.is_active = False
            item.save()
            messages.info(request, "Item retired (has historical usage; cannot hard-delete).")
        else:
            item.delete()
            messages.success(request, "Item deleted.")
        return redirect("item_list")
    return render(request, "requisitions/item_confirm_delete.html", {"item": item})


@login_required
@user_passes_test(is_staff)
def item_bulk_import(request):
    if request.method == "POST":
        csv_file = request.FILES.get("csv_file")
        if not csv_file:
            messages.error(request, "No file uploaded.")
            return redirect("item_bulk_import")
        import csv, io
        decoded = csv_file.read().decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        created, skipped = 0, 0
        for row in reader:
            name = (row.get("item_name") or "").strip()
            if not name:
                continue
            obj, was_created = Item.objects.get_or_create(
                item_name=name,
                defaults={
                    "category":     (row.get("category") or "misc").strip(),
                    "default_unit": (row.get("default_unit") or "pcs").strip(),
                    "is_active":    True,
                },
            )
            if was_created:
                created += 1
            else:
                skipped += 1
        messages.success(request, f"Imported {created} new items, {skipped} skipped (duplicates).")
        return redirect("item_list")
    return render(request, "requisitions/item_bulk_import.html")


# ---------- Reports ----------

def _get_report_queryset(date_from, date_to, dept_id):
    qs = (
        FormSubmission.objects
        .select_related("user", "user__department")
        .prefetch_related("line_items__item")
        .order_by("submission_date", "user__department__department_name")
    )
    if date_from:
        qs = qs.filter(submission_date__gte=date_from)
    if date_to:
        qs = qs.filter(submission_date__lte=date_to)
    if dept_id:
        qs = qs.filter(user__department__id=dept_id)
    return qs


@login_required
@user_passes_test(is_staff)
def report_list(request):
    date_from = request.GET.get("date_from", "")
    date_to   = request.GET.get("date_to", "")
    dept_id   = request.GET.get("dept_id", "")

    submissions = _get_report_queryset(date_from, date_to, dept_id)
    departments = Department.objects.select_related("user").order_by("department_name")

    # Summary: total line items across filtered submissions
    total_submissions = submissions.count()
    total_line_items  = sum(s.line_items.count() for s in submissions)

    paginator = Paginator(submissions, 20)
    page = paginator.get_page(request.GET.get("page"))

    return render(request, "requisitions/report_list.html", {
        "page_obj":         page,
        "departments":      departments,
        "date_from":        date_from,
        "date_to":          date_to,
        "dept_id":          dept_id,
        "total_submissions": total_submissions,
        "total_line_items":  total_line_items,
    })


@login_required
@user_passes_test(is_staff)
def report_print(request):
    date_from = request.GET.get("date_from", "")
    date_to   = request.GET.get("date_to", "")
    dept_id   = request.GET.get("dept_id", "")

    submissions = _get_report_queryset(date_from, date_to, dept_id)
    departments = Department.objects.select_related("user").order_by("department_name")

    dept_label = ""
    if dept_id:
        try:
            dept_label = Department.objects.get(id=dept_id).department_name
        except Department.DoesNotExist:
            pass

    return render(request, "requisitions/report_print.html", {
        "submissions": submissions,
        "date_from":   date_from,
        "date_to":     date_to,
        "dept_label":  dept_label,
        "printed_at":  timezone.now(),
    })


@login_required
@user_passes_test(is_staff)
def mark_delivered(request, submission_id):
    if request.method == "POST":
        submission = get_object_or_404(FormSubmission, id=submission_id)
        if submission.status == FormSubmission.STATUS_DELIVERED:
            submission.status = FormSubmission.STATUS_PENDING
        else:
            submission.status = FormSubmission.STATUS_DELIVERED
        submission.save(update_fields=["status"])
    next_url = request.POST.get("next", "")
    if next_url:
        return redirect(next_url)
    return redirect("report_list")


@login_required
@user_passes_test(is_staff)
def report_export_csv(request):
    date_from = request.GET.get("date_from", "")
    date_to   = request.GET.get("date_to", "")
    dept_id   = request.GET.get("dept_id", "")

    submissions = _get_report_queryset(date_from, date_to, dept_id)

    filename = "requisitions"
    if date_from:
        filename += f"_from_{date_from}"
    if date_to:
        filename += f"_to_{date_to}"
    filename += ".csv"

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        "Date", "Department", "Username",
        "Item", "Category", "Quantity", "Unit",
        "Submitted At", "Last Updated",
    ])

    for sub in submissions:
        dept_name = getattr(getattr(sub.user, "department", None), "department_name", "—")
        sub_at    = sub.submitted_at.strftime("%Y-%m-%d %H:%M")
        upd_at    = sub.updated_at.strftime("%Y-%m-%d %H:%M")
        items     = sub.line_items.all()
        if items:
            for li in items:
                writer.writerow([
                    sub.submission_date,
                    dept_name,
                    sub.user.username,
                    li.item.item_name,
                    li.item.get_category_display(),
                    li.quantity,
                    li.unit,
                    sub_at,
                    upd_at,
                ])
        else:
            writer.writerow([
                sub.submission_date, dept_name, sub.user.username,
                "", "", "", "", sub_at, upd_at,
            ])

    return response
