from datetime import timedelta
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.utils import timezone

"""Choices that will be reused"""
LEVEL_CHOICES = [
    ('beginner', 'Beginner'),
    ('intermediate', 'Intermediate'),
    ('advanced', 'Advanced'),
]

"""Users Table:For everything users related"""
class MyUser(AbstractUser):
    email = models.EmailField(unique=True)
    country=models.CharField(max_length=30,null=True, blank=True)
    city = models.CharField(max_length=30, null=True, blank=True)
    # device_info = models.CharField(max_length=30,null=True, blank=True)
    display_name=CharField(unique=True, max_length=255, blank=True, null=True)
    profile_picture = models.ImageField(upload_to='profile_pictures', blank=True, null=True)
    accepted_terms_and_conditions=models.BooleanField(default=False, blank=False, null=False)
    languages_spoken = models.JSONField(
        default=dict,
        blank=True,
        null=True,
        help_text="Stores languages and proficiency levels as {'english': 'fluent', 'spanish': 'intermediate'}"
    )
    otp = models.CharField(unique=True, blank=True, null=True, max_length=6)
    otp_expiry = models.DateTimeField(blank=True, null=True)
    verified_at=models.DateTimeField(blank=True, null=True)

    """In case the user decides to update their existing email with a new one"""
    updated_email=models.EmailField(unique=True, blank=True, null=True)
    scheduled_deletion_date=models.DateTimeField(blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']

    def __str__(self):
        return self.email

""""Legal Items table:For everything legal including privacy policy and terms and conditions"""
class LegalItem(models.Model):
    privacy_policy = models.TextField(blank=True, null=True, default='Privacy Policy')
    terms_and_conditions = models.TextField(blank=True, null=True,default='Terms and Conditions')
    added_on = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField()

    def __str__(self):
        return "Legal items were added successfully"

""""Legal the subscription plans"""
class SubscriptionItem(models.Model):
    CURRENCY_CHOICES = [
        ('KShs.', 'KShs.'),
        ('$', '$'),
    ]

    currency = models.CharField(max_length=20, choices=CURRENCY_CHOICES)
    monthly_plan= models.DecimalField(max_digits=10,decimal_places=2, default=0.00)
    yearly_plan = models.DecimalField(max_digits=10,decimal_places=2, default=0.00)

    def __str__(self):
        return "subscription items added successfully"

"""For the blogs"""
class Blog(models.Model):
    blog_image=models.FileField(upload_to='blog-images', blank=True, null=True)
    blog_title = models.CharField(max_length=255)
    blog_content = models.TextField()
    blog_author = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.blog_title

"""The courses models begin here"""
class Course(models.Model):
    course_name=models.CharField(max_length=255)
    course_level=models.CharField(choices=LEVEL_CHOICES, max_length=255, default='beginner')
    instructor_name=models.CharField(max_length=255)
    difficulty = models.PositiveSmallIntegerField(default=1, editable=False)

    def save(self, *args, **kwargs):
        level_map = {'beginner': 1, 'intermediate': 2, 'advanced': 3}
        self.difficulty = level_map.get(self.course_level, 0)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.course_name} - {self.course_level}"

    class Meta:
        ordering = ['course_name','difficulty']


"""To allow students to enroll for the courses"""
class EnrolledCourses(models.Model):
    course_name=models.ForeignKey(Course,on_delete=models.CASCADE, related_name='courses')
    course_level =models.CharField(choices=LEVEL_CHOICES, max_length=255, default='beginner')
    student=models.ForeignKey(MyUser,on_delete=models.CASCADE, related_name='students')
    is_enrolled=models.BooleanField(default=False)
    is_completed=models.BooleanField(default=False)
    enrolment_date = models.DateTimeField(auto_now_add=True)
    completion_date=models.DateTimeField(blank=True, null=True)
    course_progress = models.FloatField(default=0.0)

    class Meta:
        unique_together = ('student', 'course_name', 'course_level')

    def save(self, *args, **kwargs):
        if self.is_completed and self.completion_date is None:
            self.completion_date = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.course_name.course_name

"""Contains all the modules for the respective courses"""
class CourseModule(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='course_modules')
    module_title = models.CharField(max_length=255)
    module_description = models.TextField()
    module_order = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.module_title} - {self.course}"


class ModuleProgress(models.Model):
    student = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='student')
    module = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='modules')
    module_progress = models.FloatField(default=0.0) 
    is_completed = models.BooleanField(default=False)
    class Meta:
        unique_together = ('student', 'module')
    
    def __str__(self):
        return self.student.first_name

"""Contains all the lessons for the respective modules"""
class CourseLesson(models.Model):
    LESSON_CHOICES = [
        ('video', 'Video'),
        ('audio', 'Audio'),
        ('read', 'Read'),
        ('quiz', 'Quiz'),
    ]
    module_name = models.ForeignKey(CourseModule, on_delete=models.CASCADE, related_name='module_lessons')
    lesson_description = models.TextField()
    lesson_number = models.IntegerField()
    lesson_type = models.CharField(max_length=255, choices=LESSON_CHOICES, default='read')
    lesson_file = models.FileField(upload_to='course-lessons', blank=True, null=True)
    lesson_transcript = models.TextField(blank=True, null=True)
    lesson_content = models.TextField(blank=True, null=True)
    lesson_duration = models.FloatField(blank=True, null=True, help_text="Duration of the lesson in minutes")
    lesson_completed=models.BooleanField(default=False)

    def __str__(self):
        return f"{self.module_name.module_title} - {self.lesson_description}"

class LessonCompletion(models.Model):
    lesson_student = models.ForeignKey(MyUser, on_delete=models.CASCADE, related_name='lesson_student')
    lesson=models.ForeignKey(CourseLesson, on_delete=models.CASCADE, related_name='lessons')
    completed_at=models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('lesson_student', 'lesson')

    def __str__(self):
        return f"{self.lesson_student.username} completed {self.lesson.lesson_description}"
"""The course models end here"""
