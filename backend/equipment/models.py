from django.db import models


class Dataset(models.Model):
	file = models.FileField(upload_to='uploads/')
	filename = models.CharField(max_length=255)
	uploaded_at = models.DateTimeField(auto_now_add=True)
	summary = models.JSONField(null=True, blank=True)
	report = models.CharField(max_length=500, null=True, blank=True)

	def __str__(self):
		return f"{self.filename} ({self.uploaded_at:%Y-%m-%d %H:%M})"
