from django.db.models.signals import post_save, post_delete, pre_save
from django.dispatch import receiver
from lugha_app.models import *

from moviepy import VideoFileClip, AudioFileClip
import os
import logging
from django.core.files.storage import default_storage
from django.core.exceptions import ValidationError

import whisper
from pathlib import Path

from django.db import transaction

logger = logging.getLogger(__name__)

@receiver([post_save, post_delete], sender=LessonCompletion)
def update_course_completion(sender, instance, **kwargs):
    """
    Signal handler to update course and module completion status
    when a lesson is completed or uncompleted.
    """
    course = instance.lesson.module_name.course
    course_module = instance.lesson.module_name
    student = instance.lesson_student

    with transaction.atomic():
        # Total lessons in the course
        total_lessons = CourseLesson.objects.filter(
            module_name__course=course
        ).count()

        # Total lessons in the specific module
        module_total_lessons = CourseLesson.objects.filter(
            module_name=course_module
        ).count()

        if total_lessons == 0 or module_total_lessons == 0:
            return

        # Completed lessons in the course
        completed_lessons = LessonCompletion.objects.filter(
            lesson_student=student,
            lesson__module_name__course=course
        ).count()

        # Completed lessons in the module
        module_completed_lessons = LessonCompletion.objects.filter(
            lesson_student=student,
            lesson__module_name=course_module
        ).count()

        # Progress percentages
        completion_percentage = (completed_lessons / total_lessons) * 100
        module_completion_percentage = (module_completed_lessons / module_total_lessons) * 100

        try:
            # Update course enrollment progress
            enrollment = EnrolledCourses.objects.get(
                student=student,
                course_name=course
            )
            enrollment.course_progress = completion_percentage
            enrollment.is_completed = (completed_lessons == total_lessons)
            enrollment.save()

            progress_obj, created = ModuleProgress.objects.get_or_create(
                student=student,
                module=course_module
            )
            progress_obj.module_progress = module_completion_percentage
            progress_obj.is_completed = (module_completed_lessons == module_total_lessons)
            progress_obj.save()

            print(progress_obj.module_progress)

        except EnrolledCourses.DoesNotExist:
            pass


"""For extracting duration of audios and videos when uploaded"""
@receiver(post_save, sender=CourseLesson)
def handle_media_duration(sender, instance, created, **kwargs):
    """
    Handle duration extraction AFTER the file is saved
    """
    if not instance.lesson_file:
        return
        
    if instance.lesson_type not in ['video', 'audio']:
        return
        
    try:
        file_path = default_storage.path(instance.lesson_file.name)
    except NotImplementedError:
        logger.warning("Remote storage detected - duration extraction may not work")
        return
    except Exception as e:
        logger.error(f"Error accessing file path: {e}")
        return
        
    try:
        file_path = os.path.abspath(file_path)
        if not os.path.exists(file_path):
            logger.error(f"File not found at {file_path}")
            return
            
        extension = os.path.splitext(file_path)[1].lower()
        
        # Process video files
        if instance.lesson_type == 'video' and extension in ['.mp4', '.mov', '.avi', '.mkv', '.webm']:
            try:
                with VideoFileClip(file_path) as clip:
                    duration = round(clip.duration / 60, 2)
                    CourseLesson.objects.filter(pk=instance.pk).update(lesson_duration=duration)
            except Exception as e:
                logger.error(f"Video processing error: {e}")
        
        # Process audio files
        elif instance.lesson_type == 'audio' and extension in ['.mp3', '.wav', '.ogg', '.m4a']:
            try:
                with AudioFileClip(file_path) as clip:
                    duration = round(clip.duration / 60, 2)
                    CourseLesson.objects.filter(pk=instance.pk).update(lesson_duration=duration)
            except Exception as e:
                logger.error(f"Audio processing error: {e}")
                
    except Exception as e:
        logger.error(f"General processing error: {e}")

"""For transcribing the audio and video lesson files"""
@receiver(post_save, sender=CourseLesson)
def handle_transcription(sender, instance, created, **kwargs):

    if not instance.lesson_file or instance.lesson_type not in ["audio", "video"]:
        return

    try:
        model = whisper.load_model("base")
        file_path = default_storage.path(instance.lesson_file.name)
        audio = whisper.load_audio(file_path)

        result = model.transcribe(audio)
        CourseLesson.objects.filter(pk=instance.pk).update(lesson_transcript=result["text"])
        return result["text"]      
        
    except Exception as e:
        print(f"Transcription failed with: {e}")
    finally:        
        print("Done")