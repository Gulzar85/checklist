from rest_framework import serializers
from .models import (
    Restaurant, Audit, Section, Question,
    AuditSection, AuditQuestionResponse, CorrectiveAction
)


class RestaurantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = '__all__'


class QuestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Question
        fields = '__all__'


class SectionSerializer(serializers.ModelSerializer):
    questions = QuestionSerializer(many=True, read_only=True)

    class Meta:
        model = Section
        fields = '__all__'


class AuditQuestionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditQuestionResponse
        fields = '__all__'


class AuditSectionSerializer(serializers.ModelSerializer):
    responses = AuditQuestionResponseSerializer(many=True, read_only=True)

    class Meta:
        model = AuditSection
        fields = '__all__'


class AuditSerializer(serializers.ModelSerializer):
    sections = AuditSectionSerializer(many=True, read_only=True)
    restaurant_name = serializers.CharField(source='restaurant.name', read_only=True)
    auditor_name_display = serializers.CharField(source='auditor_name.get_full_name', read_only=True)

    class Meta:
        model = Audit
        fields = '__all__'


class AuditCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Audit
        fields = ['restaurant', 'audit_date', 'manager_on_duty']


class CorrectiveActionSerializer(serializers.ModelSerializer):
    audit_restaurant = serializers.CharField(source='audit.restaurant.name', read_only=True)
    question_text = serializers.CharField(source='question_response.question.question_text', read_only=True)

    class Meta:
        model = CorrectiveAction
        fields = '__all__'