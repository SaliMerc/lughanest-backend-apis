from django.contrib.auth import password_validation
from rest_framework import serializers
import lugha_app.models as models
from .models import MyUser, LessonCompletion, EnrolledCourses
from django.db.models.functions import TruncDay, TruncMonth
from django.db.models import Count
from datetime import timedelta
from django.utils import timezone

class UserSerializer(serializers.ModelSerializer):
    profile_picture_url = serializers.SerializerMethodField()

    class Meta:
        model = MyUser
        fields = ['id', 'username', 'email','first_name','last_name','display_name','city','country','is_active','profile_picture','profile_picture_url','accepted_terms_and_conditions','languages_spoken','updated_email']

    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return None

    def create(self, validated_data):
        validated_data.pop('is_active', None)
        user=MyUser.objects.create_user(**validated_data, is_active=False)
        return user

class UserProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyUser
        fields = ['email','display_name', 'profile_picture', 'languages_spoken']
    
class BlogSerializer(serializers.ModelSerializer):
    blog_image_url = serializers.SerializerMethodField()

    def get_blog_image_url(self, obj):
        request = self.context.get('request')
        if obj.blog_image and request:
            return request.build_absolute_uri(obj.blog_image.url)
        return None

    class Meta:
        model = models.Blog
        fields = ['id', 'blog_title', 'blog_content', 'blog_author', 'created_at', 'blog_image_url']

class LegalItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LegalItem
        fields = ['id', 'privacy_policy', 'terms_and_conditions', 'updated_at']

class SubscriptionItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.SubscriptionItem
        fields = ['currency','monthly_plan', 'yearly_plan']

class CourseItemsSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Course
        fields = ['id', 'course_name', 'course_level', 'instructor_name']

class EnrollCourseItemsSerializer(serializers.ModelSerializer):
    course_name_id = serializers.PrimaryKeyRelatedField(
        queryset=models.Course.objects.all(),
        source='course_name',
        write_only=True
    )

    course_name = CourseItemsSerializer(read_only=True)

    class Meta:
        model = models.EnrolledCourses
        fields = ['id', 'course_name_id','course_name', 'course_level','enrolment_date', 'is_enrolled', 'is_completed','completion_date','course_progress']

    def create(self,validated_data):
        validated_data['student'] = self.context['request'].user
        return super().create(validated_data)
    
class PartnerUserSerializer(serializers.ModelSerializer):
    courses = serializers.SerializerMethodField()
    profile_picture_url = serializers.SerializerMethodField()
    
    class Meta:
        model = MyUser
        fields = ['id', 'username', 'display_name', 'profile_picture_url', 'courses']
    
    def get_profile_picture_url(self, obj):
        request = self.context.get('request')
        if obj.profile_picture and request:
            return request.build_absolute_uri(obj.profile_picture.url)
        return None
    
    def get_courses(self, obj):
        # Get the user's enrolled courses
        user_courses = EnrolledCourses.objects.filter(
            student=obj
        ).select_related('course_name').order_by('-enrolment_date')
        
        return [
            {
                'course_name': course.course_name.course_name,
                'course_level': course.course_level,
                'enrolment_date': course.enrolment_date
            }
            for course in user_courses
        ]

class DashboardGraphSerializer(serializers.Serializer):
    def get_weekly_lessons_data(self, user):
        today = timezone.now().date()
        start_of_week = today - timedelta(days=today.weekday())
        end_of_week = start_of_week + timedelta(days=6)

        weekly_lesson_completion = LessonCompletion.objects.filter(
            lesson_student=user, 
            completed_at__gte=start_of_week,
            completed_at__lte=end_of_week
        )

        lessons_completed_by_week = weekly_lesson_completion.annotate(
            week=TruncDay('completed_at')
        ).values('week').annotate(
            total_lessons=Count('id')
        ).order_by('week')

        weekly_lessons_data = {
            'labels': [entry['week'].strftime('%a') for entry in lessons_completed_by_week],
            'data': [entry['total_lessons'] for entry in lessons_completed_by_week]
        }

        weekly_labels = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
        weekly_lessons_data = [
            weekly_lessons_data['data'][weekly_lessons_data['labels'].index(label)] 
            if label in weekly_lessons_data['labels'] else 0 
            for label in weekly_labels
        ]
        
        return weekly_lessons_data

    def get_monthly_lessons_data(self, user):
        today = timezone.now().date()
        start_of_year = today.replace(month=1, day=1)
        end_of_year = today.replace(month=12, day=31)

        monthly_lesson_completion = LessonCompletion.objects.filter(
            lesson_student=user,
            completed_at__gte=start_of_year,
            completed_at__lte=end_of_year
        )

        lessons_by_month = monthly_lesson_completion.annotate(
            month=TruncMonth('completed_at')
        ).values('month').annotate(
            total_lessons_by_month=Count('id')
        ).order_by('month')

        lessons_by_month_data = {
            'labels': [entry['month'].strftime('%b') for entry in lessons_by_month],
            'data': [entry['total_lessons_by_month'] for entry in lessons_by_month]
        }

        monthly_common_labels = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 
                                'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        
        lessons_by_month_data = [
            lessons_by_month_data['data'][lessons_by_month_data['labels'].index(label)] 
            if label in lessons_by_month_data['labels'] else 0 
            for label in monthly_common_labels
        ]
        
        return lessons_by_month_data


class CourseLessonCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LessonCompletion
        fields = ['id', 'lesson_student', 'lesson', 'completed_at']
        read_only_fields = ['lesson_student'] 

    def validate(self, attrs):
        attrs['lesson_student'] = self.context['request'].user
        return attrs

class CourseLessonsSerializer(serializers.ModelSerializer):
    lesson_file_url = serializers.SerializerMethodField()

    
    class Meta:
        model = models.CourseLesson
        fields = ['id', 'module_name', 'lesson_number','lesson_description','lesson_type','lesson_file_url','lesson_transcript','lesson_content','lesson_duration','lesson_completed']

    def get_lesson_file_url (self, obj: models.CourseLesson):
        request = self.context.get('request')
        if obj.lesson_file and request:
            return request.build_absolute_uri(obj.lesson_file.url)
        return None

class CourseModuleCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.ModuleProgress
        fields = ['id','module','module_progress']
        read_only_fields = ['student']

class CourseModulesSerializer(serializers.ModelSerializer):
    module_lessons = CourseLessonsSerializer(many=True, read_only=True)
    modules = CourseModuleCompletionSerializer(many=True, read_only=True)

    class Meta:
        model = models.CourseModule
        fields = ['id', 'course', 'module_title', 'module_description', 
                 'module_lessons', 'modules']



