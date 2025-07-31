from django.db import models

class Article(models.Model):
    pmid        = models.CharField(max_length=20, unique=True)
    title       = models.TextField()
    abstract    = models.TextField()
    pub_date    = models.DateField()
    raw_json    = models.JSONField()

class Summary(models.Model):
    article     = models.OneToOneField(Article, on_delete=models.CASCADE)
    text        = models.TextField()
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Summaries"

class Validation(models.Model):
    summary     = models.OneToOneField(Summary, on_delete=models.CASCADE)
    hallucination_score = models.IntegerField()
    issues      = models.JSONField()   # list of unsupported claims

class TrendReport(models.Model):
    generated_on = models.DateTimeField(auto_now_add=True)
    text         = models.TextField()
    issues       = models.JSONField()   # flagged statements