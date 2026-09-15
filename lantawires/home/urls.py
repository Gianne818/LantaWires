from django.urls import path
from . import views

app_name = "home"

urlpatterns = [
    path("", views.home_view, name="index"),
    path("logout/", views.logout_view, name="logout"),
    path("api/report/", views.create_report_api, name="create_report"),
    path("api/status/", views.update_status_api, name="update_status"),
]
