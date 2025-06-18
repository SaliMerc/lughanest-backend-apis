# lugha_app/receivers.py
from lugha_app.models import *
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.apps import apps

@receiver(post_save, sender=LessonCompletion)
def update_course_completion(sender, instance, created, **kwargs):
    """
    Signal handler to update course completion status when a lesson is completed.
    """  
    if created: 
       
        course = instance.lesson.module_name.course
        student = instance.lesson_student
        
        # Getting all lessons in the course
        total_lessons = CourseLesson.objects.filter(
            module_name__course=course
        ).count()
        
        if total_lessons == 0:
            return
        
        completed_lessons = LessonCompletion.objects.filter(
            lesson_student=student,
            lesson__module_name__course=course
        ).count()
        
        completion_percentage = (completed_lessons / total_lessons) * 100
        
        try:
            enrollment = EnrolledCourses.objects.get(
                student=student,
                course_name=course
            )
            
            if completed_lessons >= total_lessons and not enrollment.is_completed:
                enrollment.is_completed = True
                enrollment.save()
            
            if hasattr(enrollment, 'progress'):
                enrollment.progress = completion_percentage
                enrollment.save()
                
        except EnrolledCourses.DoesNotExist:
            pass