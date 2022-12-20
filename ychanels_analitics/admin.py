from django.contrib import admin
from .models import Video, Analytics, Channel, ChannelAnalytics

# Register your models here.
admin.site.register(Video)
admin.site.register(Analytics)
admin.site.register(Channel)
admin.site.register(ChannelAnalytics)
