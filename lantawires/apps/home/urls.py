from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    path("", views.home_view, name="home"),
    path("", views.home_view, name="index"),
    path("my-reports/", views.my_reports_view, name="my_reports"),
    path("dispatches/", views.dispatches_view, name="dispatches"),
    path("dispatches/export/", views.export_dispatches_csv, name="export_dispatches_csv"),
    path("logout/", views.logout_view, name="logout"),
    path("api/report/", views.create_report_api, name="create_report"),
    path("api/report/<int:report_id>/edit/", views.edit_report_api, name="edit_report"),
    path("api/report/<int:report_id>/delete/", views.delete_report_api, name="delete_report"),
    path("api/status/", views.update_status_api, name="update_status"),
    path("api/dispatch/", views.update_dispatch_api, name="update_dispatch"),
    path("api/dispatch/create/", views.create_dispatch_api, name="create_dispatch"),
]
