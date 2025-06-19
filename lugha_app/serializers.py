from django.contrib.auth import password_validation
from rest_framework import serializers
import lugha_app.models as models
from .models import MyUser

class UserSerializer(serializers.ModelSerializer):
    profile_picture = serializers.ImageField(use_url=True)

    class Meta:
        model = MyUser
        fields = ['id', 'username', 'email', 'password','first_name','last_name','display_name','city','country','is_active','profile_picture','accepted_terms_and_conditions','languages_spoken']

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
        fields = ['id', 'course_name_id','course_name', 'course_level','enrolment_date', 'is_enrolled', 'is_completed','completion_date']

    def create(self,validated_data):
        validated_data['student'] = self.context['request'].user
        return super().create(validated_data)


class CourseLessonCompletionSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.LessonCompletion
        fields = ['id', 'lesson_student', 'lesson', 'completed_at']
        read_only_fields = ['lesson_student'] 

    def validate(self, attrs):
        attrs['lesson_student'] = self.context['request'].user
        return attrs

class CourseLessonsSerializer(serializers.ModelSerializer):
     class Meta:
        model = models.CourseLesson
        fields = ['id', 'module_name', 'lesson_number','lesson_description','lesson_type','lesson_file','lesson_transcript','lesson_content','lesson_duration','lesson_completed']

class CourseModulesSerializer(serializers.ModelSerializer):
    module_lessons = CourseLessonsSerializer(many=True, read_only=True)

    class Meta:
        model = models.CourseModule
        fields = ['id', 'course', 'module_title','module_description','module_lessons','module_progress']




