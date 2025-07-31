from django.contrib import admin
from .models import Article, Summary, Validation, TrendReport


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("pmid", "title", "pub_date")
    search_fields = ("pmid", "title")
    list_filter = ("pub_date",)


@admin.register(Summary)
class SummaryAdmin(admin.ModelAdmin):
    list_display = ("article", "created_at", "text_snippet")
    search_fields = ("article__pmid", "text")
    list_filter = ("created_at",)

    def text_snippet(self, obj):
        return obj.text[:75] + ("…" if len(obj.text) > 75 else "")

    text_snippet.short_description = "Summary Text"


@admin.register(Validation)
class ValidationAdmin(admin.ModelAdmin):
    list_display = ("summary", "hallucination_score")
    search_fields = ("summary__article__pmid",)
    list_filter = ("hallucination_score",)


@admin.register(TrendReport)
class TrendReportAdmin(admin.ModelAdmin):
    list_display = ("pk", "generated_on")
    readonly_fields = ("generated_on", "text")
    search_fields = ("text",)
    date_hierarchy = "generated_on"
