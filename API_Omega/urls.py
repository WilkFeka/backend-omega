"""
URL configuration for API_Omega project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
import Users.views as Users_views

urlpatterns = [
    path('api/admin/', admin.site.urls),

    # AUTHENTICATION
    path('api/auth/csrf/', Users_views.csrf, name='csrf'),
    path('api/auth/login/', Users_views.login_view, name='login'),
    path('api/auth/logout/', Users_views.logout_view, name='logout'),
    path('api/auth/me/', Users_views.me, name='me'),

    # USERS
    path('api/users/', Users_views.UserListCreateAPIView.as_view(), name='user-list-create'),
    path('api/users/<int:user_id>/', Users_views.UserDetailAPIView.as_view(), name='user-retrieve-update-destroy'),
]
