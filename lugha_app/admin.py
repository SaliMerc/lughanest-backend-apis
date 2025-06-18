from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(MyUser)
admin.site.register(Blog)
admin.site.register(LegalItem)
admin.site.register(Course)
admin.site.register(SubscriptionItem)
admin.site.register(EnrolledCourses)
admin.site.register(CourseModule)
admin.site.register(CourseLesson)
admin.site.register(LessonCompletion)
