from django.urls import path
from . import views
#Linking all the URL's, to allow for html insertion from views.py
urlpatterns = [
    path('', views.bestFlight, name='index'),
    path('prices/', views.main, name='prices')

]