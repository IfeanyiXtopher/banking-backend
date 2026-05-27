from django.urls import path

from . import views

urlpatterns = [
    path('savings-goals/', views.SavingsGoalListCreateView.as_view(), name='savings-goal-list'),
    path('savings-goals/<uuid:pk>/', views.SavingsGoalDetailView.as_view(), name='savings-goal-detail'),
    path('savings-goals/<uuid:pk>/cancel/', views.savings_goal_cancel, name='savings-goal-cancel'),
    path('savings-goals/<uuid:pk>/allocate/', views.savings_goal_allocate, name='savings-goal-allocate'),
]
