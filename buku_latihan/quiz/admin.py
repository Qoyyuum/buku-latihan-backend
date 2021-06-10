from django.contrib import admin

from .models import Quiz, Question, Progress, Sitting, Category, SubCategory

admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Progress)
admin.site.register(Sitting)
admin.site.register(Category)
admin.site.register(SubCategory)