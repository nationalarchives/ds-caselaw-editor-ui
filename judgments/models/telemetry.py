from django.db import models


class RunStatus(models.TextChoices):
    STARTED = "STA", "Started"
    FAILED = "FAI", "Failed"
    FINISHED = "FIN", "Finished"


class BulkReparseRunLog(models.Model):
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)

    documents_in_queue = models.IntegerField()
    target_parser_version = models.TextField()

    documents_selected = models.IntegerField(null=True)
    documents_attempted = models.IntegerField(null=True)
    documents_skipped = models.IntegerField(null=True)
    documents_failed = models.IntegerField(null=True)

    status = models.CharField(
        max_length=3,
        choices=RunStatus,
        blank=True,
    )

    detail = models.TextField(blank=True)

    class Meta:
        verbose_name = "Bulk Reparse Run Log"
        verbose_name_plural = "Bulk Reparse Run Logs"
        ordering = ["-start_time"]

    def __str__(self):
        return f"Bulk Reparse Run - {self.start_time}"
