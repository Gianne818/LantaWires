from django.contrib import admin
from django.urls import include, path

from apps.home import views as home_views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", include("apps.login.urls")),
    path("register/", include("apps.register.urls")),
    path("", home_views.home_view, name="root"),
    path("api/report/", home_views.create_report_api, name="root_create_report"),
    path("api/status/", home_views.update_status_api, name="root_update_status"),
    path("home/", include("apps.home.urls")),
    path("profile/", include("apps.profile.urls")),
    path("settings/", include("apps.user_settings.urls")),
]
