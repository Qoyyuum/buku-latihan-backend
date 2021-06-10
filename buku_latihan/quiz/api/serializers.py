from rest_framework import serializers
from quiz.models import Category, SubCategory, Quiz, Progress, Sitting, Question

class CategorySerializer(serializers.ModelSerializer):

	class Meta:
		model = Category
		fields = '__all__'

class SubCategorySerializer(serializers.ModelSerializer):

	class Meta:
		model = SubCategory
		fields = '__all__'

class QuizSerializer(serializers.ModelSerializer):

	class Meta:
		model = Quiz
		fields = '__all__'
class ProgressSerializer(serializers.ModelSerializer):

	class Meta:
		model = Progress
		fields = '__all__'

class SittingSerializer(serializers.ModelSerializer):

	class Meta:
		model = Sitting
		fields = '__all__'

class QuestionSerializer(serializers.ModelSerializer):

	class Meta:
		model = Question
		fields = '__all__'