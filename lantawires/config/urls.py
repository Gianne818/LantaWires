from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("login/", include("apps.login.urls")),
    path("register/", include("apps.register.urls")),
    path("", include("apps.home.urls")),
    path("profile/", include("apps.profile.urls")),
    path("settings/", include("apps.user_settings.urls")),
]
