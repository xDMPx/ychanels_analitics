from django.db import models

# Create your models here.
class Channel(models.Model):
    channel_id = models.CharField(max_length=100)
    name = models.CharField(max_length=100)

class Video(models.Model):
    video_id = models.CharField(max_length=11)
    title = models.CharField(max_length=100)
    channel = models.ForeignKey(Channel, on_delete=models.CASCADE, blank=True, null=True) 

class Analytics(models.Model):
    video = models.ForeignKey(
            Video,
            on_delete=models.CASCADE)
    time_stamp = models.DateTimeField()
    view_count = models.PositiveBigIntegerField()
    likes_count = models.PositiveBigIntegerField()
    dislikes_count = models.PositiveBigIntegerField()
    comment_count = models.PositiveBigIntegerField()

class ChannelAnalytics(models.Model):
    channel = models.ForeignKey(Channel,on_delete=models.CASCADE)
    subscriber_count = models.PositiveBigIntegerField()
    time_stamp = models.DateTimeField()

