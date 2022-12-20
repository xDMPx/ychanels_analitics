from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path("videos/<str:video_id>", views.videos, name="videos"),
    path("videos-pdf/<str:video_id>/<int:year>/<int:month>/<int:day>", views.download_video_pdf, name="videos-pdf"),
    path("videos-historical/<str:video_id>/<int:year>/<int:month>/<int:day>", views.videos_historical, name="videos-historical"),
    path("channels/<str:channel_id>", views.channels, name="channels"),
    path("channels-historical/<str:channel_id>/<int:year>/<int:month>/<int:day>", views.channels_historical, name="channels-historical"),
    path("channels-pdf/<str:channel_id>/<int:year>/<int:month>/<int:day>", views.download_channel_pdf, name="channels-pdf")
]
