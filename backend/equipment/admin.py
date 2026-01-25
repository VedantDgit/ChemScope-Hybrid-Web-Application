from django.contrib import admin
# Register your models here.
from .models import Dataset


@admin.register(Dataset)
class DatasetAdmin(admin.ModelAdmin):
	list_display = ('filename', 'uploaded_at')
	readonly_fields = ('uploaded_at',)
# Register your models here.
