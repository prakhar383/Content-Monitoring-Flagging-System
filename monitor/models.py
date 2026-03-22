from django.db import models


class Keyword(models.Model):
    name = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name


class ContentItem(models.Model):
    title        = models.CharField(max_length=300)
    source       = models.CharField(max_length=100)
    body         = models.TextField()
    last_updated = models.DateTimeField()

    def __str__(self):
        return self.title


class Flag(models.Model):

    STATUS_CHOICES = [
        ('pending',    'Pending'),
        ('relevant',   'Relevant'),
        ('irrelevant', 'Irrelevant'),
    ]

    keyword      = models.ForeignKey(Keyword,     on_delete=models.CASCADE)
    content_item = models.ForeignKey(ContentItem, on_delete=models.CASCADE)
    score        = models.IntegerField(default=0)
    status       = models.CharField(
                       max_length=20,
                       choices=STATUS_CHOICES,
                       default='pending'
                   )
    reviewed_at  = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('keyword', 'content_item')

    def __str__(self):
        return f"{self.keyword.name} → {self.content_item.title} [{self.status}]"