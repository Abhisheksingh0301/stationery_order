from django.urls import path
from . import views

urlpatterns = [
    path("",                                    views.login_view,        name="login"),
    path("login/",                              views.login_view,        name="login"),
    path("logout/",                             views.logout_view,       name="logout"),
    path("dashboard/",                          views.dashboard,         name="dashboard"),
    path("history/",                            views.submission_history, name="history"),
    path("form/new/",                           views.create_form,       name="create_form"),
    path("form/<int:submission_id>/edit/",      views.edit_form,         name="edit_form"),
    path("form/<int:submission_id>/success/",   views.success_view,      name="success"),
    path("form/<int:submission_id>/print/",    views.form_print,        name="form_print"),

    # Department Master
    path("departments/",                        views.department_list,   name="department_list"),
    path("departments/new/",                    views.department_create, name="department_create"),
    path("departments/<int:dept_id>/edit/",     views.department_edit,   name="department_edit"),
    path("departments/<int:dept_id>/delete/",   views.department_delete, name="department_delete"),

    # Reports
    path("reports/",                                        views.report_list,       name="report_list"),
    path("reports/print/",                                  views.report_print,      name="report_print"),
    path("reports/export/csv/",                             views.report_export_csv, name="report_export_csv"),
    path("reports/<int:submission_id>/mark-delivered/",     views.mark_delivered,    name="mark_delivered"),

    # Item Master
    path("items/",                              views.item_list,         name="item_list"),
    path("items/new/",                          views.item_create,       name="item_create"),
    path("items/<int:item_id>/edit/",           views.item_edit,         name="item_edit"),
    path("items/<int:item_id>/delete/",         views.item_delete,       name="item_delete"),
    path("items/import/",                       views.item_bulk_import,  name="item_bulk_import"),
]
