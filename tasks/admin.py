from django.contrib import admin
from .models import Defect, OrderComponent, WorkStep
from .models import Order, CodeItem, Procedure, Tool, Component, Profile

class TaskAdmin(admin.ModelAdmin):
    readonly_fields = ('created', )

admin.site.register(Order)
admin.site.register(CodeItem)
admin.site.register(Procedure)
admin.site.register(Tool)
admin.site.register(Component)
admin.site.register(Profile)
admin.site.register(WorkStep)
admin.site.register(Defect)
admin.site.register(OrderComponent)