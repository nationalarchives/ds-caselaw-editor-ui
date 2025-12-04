from django.db import models


class BulkReparseRunLog(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)

    documents_in_queue = models.IntegerField()
    target_parser_version = models.TextField()

    documents_selected = models.IntegerField(null=True)
    documents_attempted = models.IntegerField(null=True)
    documents_skipped = models.IntegerField(null=True)
    documents_failed = models.IntegerField(null=True)

    class Meta:
        verbose_name = "Bulk Reparse Run Log"
        verbose_name_plural = "Bulk Reparse Run Logs"

    def __str__(self):
        return f"Bulk Reparse Run - {self.start_time}"
