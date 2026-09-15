from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path

def root_redirect(request):
    return redirect("login:index")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", root_redirect, name="root"),
    path("login/", include("login.urls", namespace="login")),
    path("register/", include("register.urls", namespace="register")),
    path("home/", include("home.urls", namespace="home")),
]
