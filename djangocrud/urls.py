from django.contrib import admin
from django.urls import include, path
from djangocrud import settings
from tasks import views
from django.conf.urls.static import static
from django.views.i18n import set_language
from django.conf.urls.i18n import i18n_patterns
from django.views.i18n import JavaScriptCatalog

urlpatterns = [
    path('grappelli/', include('grappelli.urls')),
    path('i18n/setlang/', set_language, name='set_language'),
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('', views.employee_login, name='employee_login'),    
    path('logout/', views.employee_logout, name='logout'),
    path('orders/<int:order_id>/', views.order_detail, name='order_detail'),
    path('orders/', views.order_search, name='order_search'),
    path('orders/<int:order_id>/verify/',
         views.verify_components, name='verify_components'),
    path('procedure/<int:procedure_id>/',
         views.procedure_detail, name='procedure_detail'),
    path('work-sequence/<int:order_id>/',
         views.work_sequence, name='work_sequence'),
    path('orders/<int:order_id>/step/<int:step_number>/',
         views.work_step_view, name='work_step_view'),
    path('orders/<int:order_id>/step/<int:step_id>/report_defect/',
         views.report_step_defect, name='report_step_defect'),
    path('orders/<int:order_id>/steps/<int:step_id>/update/',
         views.update_step_progress, name='update_step_progress'),
    path('order-completed/<int:order_id>',
         views.order_completed, name='order_completed'),
    path('orders/<int:order_id>/reopen/',
         views.reopen_order, name='reopen_order'),
    path('orders/<int:order_id>/toggle_component/<int:component_id>/',
         views.toggle_component, name='toggle_component'),
    path('order/<int:order_id>/change_quantity/',
         views.change_order_quantity, name='change_order_quantity'),
    path('work_step/<int:order_id>/<int:step_number>/read_pcan/',
          views.read_pcan, name='read_pcan'),
    path("work_step/<int:order_id>/<int:step_number>/read_pcan_values/",
         views.read_pcan_values, name="read_pcan_values"), 
    path("read_pcan_live/", views.read_pcan_live, name="read_pcan_live"),
    ]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,
                          document_root=settings.MEDIA_ROOT)
