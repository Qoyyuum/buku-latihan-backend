from django.contrib import admin

from .models import Category, Progress, Question, Quiz, Sitting, SubCategory

admin.site.register(Quiz)
admin.site.register(Question)
admin.site.register(Progress)
admin.site.register(Sitting)
admin.site.register(Category)
admin.site.register(SubCategory)
