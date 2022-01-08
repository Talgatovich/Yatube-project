from django.urls import path
from . import views

app_name = 'about'


# from yatube.posts import urls
urlpatterns = [
    path('author/', views.AboutAuthorView.as_view(), name='author'),
    path('tech/', views.AboutTechView.as_view(), name='tech'),

]
