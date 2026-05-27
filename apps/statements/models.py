import uuid
from django.db import models


class Statement(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    account = models.ForeignKey('accounts.Account', on_delete=models.CASCADE, related_name='statements')
    period_start = models.DateField()
    period_end = models.DateField()
    pdf_file = models.FileField(upload_to='statements/', blank=True, null=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    is_paperless = models.BooleanField(default=True)

    class Meta:
        ordering = ['-period_end']
        unique_together = ['account', 'period_start', 'period_end']

    def __str__(self):
        return f'Statement {self.period_start} to {self.period_end} — {self.account.account_number}'
