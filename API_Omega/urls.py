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
import Employees.views as Employees_views
import Salaries.views as Salaries_views

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

    # EMPLEADOS
    path('api/empleados/', Employees_views.EmployeeListCreateAPIView.as_view(), name='employee-list-create'),
    path('api/empleados/<int:employee_id>/', Employees_views.EmployeeDetailAPIView.as_view(), name='employee-retrieve-update-destroy'),
    path('api/empleados/grupos/', Employees_views.EmployeeGroupListCreateAPIView.as_view(), name='employee-group-list-create'),
    path('api/empleados/grupos/<int:group_id>/', Employees_views.EmployeeGroupDetailAPIView.as_view(), name='employee-group-detail'),

    # SALARIOS
  path('api/salarios/', Salaries_views.SalaryListCreateAPIView.as_view(), name='salary-list-create'),

path('api/salarios/<int:salary_id>/', Salaries_views.SalaryDetailAPIView.as_view(), name='salary-retrieve-update-destroy'),

path('api/salarios/empleado/<int:employee_id>/', Salaries_views.EmployeeSalaryAPIView.as_view(), name='employee-salary'),

path('api/salarios/<int:salary_id>/descuentos/', Salaries_views.SalaryDiscountListCreateAPIView.as_view(), name='salary-discount-list-create'),

path('api/salarios/<int:salary_id>/descuentos/<int:discount_id>/', Salaries_views.SalaryDiscountDetailAPIView.as_view(), name='salary-discount-detail'),

path('api/salarios/<int:salary_id>/adicionales/', Salaries_views.SalaryAdditionalListCreateAPIView.as_view(), name='salary-additional-list-create'),

path('api/salarios/<int:salary_id>/adicionales/<int:additional_id>/', Salaries_views.SalaryAdditionalDetailAPIView.as_view(), name='salary-additional-detail'),
]
