import logging
import sys
from datetime import datetime
from django.utils import timezone

from ...models import Video, Analytics, Channel, ChannelAnalytics
from django.db import connections


from django.conf import settings

class MyOutput():
    def __init__(self,sys_output, logfile):
        self.stdout = sys_output
        self.log = open(logfile, 'a')
    
    def write(self, text):
        self.log.write(text)
        self.log.flush()
        try:
            self.stdout.write(text)
        except:
            pass
            
    def close(self):
        self.log.close()
        try:
            self.stdout.close()
        except:
            pass
            
    def flush(self):
        try:
            self.stdout.flush()
        except:
            pass

import threading
import requests
import selectors

if settings.DEBUG:
    print("Debug mode")
    # Hook into the apscheduler logger
    sys.stdout = MyOutput(sys.stdout,"../stdout_log_scheduler")
    sys.stderr = MyOutput(sys.stderr,"../stderr_log_scheduler")
    logging.basicConfig(level=logging.DEBUG)

class SchedulerJob():
    piped_API_domains = [
        ""
    ]
    piped_API_domain_index = 0

    def logMessage(self, message):
        now = datetime.now()
        log_message = f"Timestamp: {now} || {message}"
        logging.info(log_message)
        logFile = open("../log_scheduler","a")
        logFile.write(f"{log_message} \n")
        logFile.close()

    def getVideoDataJSONfromPipedAPI(self, video_id):
        self.logMessage(f"Analytics for {video_id} piped API")
        video_url = self.piped_API_domains[self.piped_API_domain_index]+"/streams/"+video_id
        try:   
            response = requests.get(video_url)
            while response.status_code != 200:
                self.logMessage(f"Error for: {self.piped_API_domains[self.piped_API_domain_index]}; Status code: {response.status_code}")
                self.piped_API_domain_index += 1
                if(self.piped_API_domain_index >= len(self.piped_API_domains)-1): 
                    self.piped_API_domain_index = 0 
                self.logMessage(f"Trying {self.piped_API_domain_index}: {self.piped_API_domains[self.piped_API_domain_index]}")
                video_url = self.piped_API_domains[self.piped_API_domain_index]+"/streams/"+video_id
                response = requests.get(video_url)
            
            self.logMessage(f"API used for update: {self.piped_API_domains[self.piped_API_domain_index]} / {self.piped_API_domain_index}")
            json = response.json()
            return json
        except Exception as e:
            self.logMessage(f"Update getVideoDataJSONfromPipedAPI ERROR for vid {video_id} E: {e}")
            self.piped_API_domain_index += 1
            return self.getVideoDataJSONfromPipedAPI(video_id)

    def getCommentsDataJSONfromPipedAPI(self, video_id):
        self.logMessage(f"Comments for {video_id} piped API")
        video_url = self.piped_API_domains[self.piped_API_domain_index]+"/comments/"+video_id
        try:   
            response = requests.get(video_url)
            while response.status_code != 200:
                self.logMessage(f"Error for: {self.piped_API_domains[self.piped_API_domain_index]}; Status code: {response.status_code}")
                self.piped_API_domain_index += 1
                if(self.piped_API_domain_index >= len(self.piped_API_domains)-1): 
                    self.piped_API_domain_index = 0 
                self.logMessage(f"Trying {self.piped_API_domain_index}: {self.piped_API_domains[self.piped_API_domain_index]}")
                video_url = self.piped_API_domains[self.piped_API_domain_index]+"/comments/"+video_id
                response = requests.get(video_url)
            
            self.logMessage(f"API used for update: {self.piped_API_domains[self.piped_API_domain_index]} / {self.piped_API_domain_index}")
            json = response.json()
            return json
        except Exception as e:
            self.logMessage(f"Update getCommentsDataJSONfromPipedAPI ERROR for vid {video_id} E: {e}")
            self.piped_API_domain_index += 1
            return self.getCommentsDataJSONfromPipedAPI(video_id)

    def createAnalyticsObjectFromJson(self, video,data_json_piped, data_json_piped_comments):
        views = data_json_piped["views"]
        likes = data_json_piped["likes"]
        dislikes = data_json_piped["dislikes"]
        comment_count = data_json_piped_comments["commentCount"]
        now = timezone.localtime(timezone.now())
        if views <= 0: views = 0
        if likes <= 0: likes = 0
        if dislikes <= 0: dislikes = 0
        if comment_count <= 0: comment_count = 0
        self.logMessage(f"now: {now} ; views: {views} ; likes: {likes} ; dislikes: {dislikes} ; comment_count: {comment_count}")
        analytics = Analytics(video=video,time_stamp=now,view_count=views,likes_count=likes,dislikes_count=dislikes,comment_count=comment_count)
        return analytics
    
    def initializeAnalytics(self, video_id):
        self.piped_API_domain_index = 0
        self.logMessage("InitializeAnalytics UPDATE")
        video = Video.objects.filter(video_id=video_id)
        vid = video[0]
        try:  
            data_json_piped = self.getVideoDataJSONfromPipedAPI(vid.video_id)
            comments_data_json_piped = self.getCommentsDataJSONfromPipedAPI(vid.video_id)
            vid_analytics = self.createAnalyticsObjectFromJson(vid, data_json_piped, comments_data_json_piped)
            vid_analytics.save()
        except Exception as e:
            self.logMessage(f"Update initializeAnalytics ERROR for vid {vid.video_id} E: {e}")

    def updateData(self):
        connections.close_all()
        self.piped_API_domain_index = 0
        self.logMessage("UPDATE")
        videos = Video.objects.all()
        for vid in videos:
            try:    
                data_json_piped = self.getVideoDataJSONfromPipedAPI(vid.video_id)
                comments_data_json_piped = self.getCommentsDataJSONfromPipedAPI(vid.video_id)
                vid_analytics = self.createAnalyticsObjectFromJson(vid, data_json_piped, comments_data_json_piped)
                vid_analytics.save()
            except Exception as e:
                self.logMessage(f"Update updateData ERROR for vid {vid.video_id} E: {e}")
 
        channels = Channel.objects.all()
        for channel in channels:
            try:    
                data_json_piped = self.getChannelDataJSONfromPipedAPI(channel.channel_id)
                subscriber_count = data_json_piped['subscriberCount']
                now = timezone.localtime(timezone.now())
                if subscriber_count <= 0: subscriber_count = 0
                self.logMessage(f"now: {now} ; subscriberCount: {subscriber_count}")
                ChannelAnalytics(channel=channel,subscriber_count=subscriber_count,time_stamp=now).save()

                vid_json = data_json_piped["relatedStreams"][0]
                video_id = vid_json['url'].split("v=")[1]
                
                last_video = Video.objects.filter(channel=channel).last()
                if video_id != last_video.video_id:
                    title = vid_json['title']
                    Video(video_id=video_id,title=title,channel=channel).save()
                    self.initializeAnalytics(video_id)
                
            except Exception as e:
                self.logMessage(f"Update updateData ERROR for vid {channel.name } E: {e}")

    def getChannelDataJSONfromPipedAPI(self, channel_id):
        self.logMessage(f"Channel Analytics for {channel_id} piped API")
        channel_url = []
        if channel_id[0] == '@':
            channel_url = self.piped_API_domains[self.piped_API_domain_index]+"/c/"+channel_id
        else:
            channel_url = self.piped_API_domains[self.piped_API_domain_index]+"/channel/"+channel_id

        try:  
            response = requests.get(channel_url)
            while response.status_code != 200:
                self.logMessage(f"Error for: {self.piped_API_domains[self.piped_API_domain_index]}; Status code: {response.status_code}")
                self.piped_API_domain_index += 1
                if(self.piped_API_domain_index >= len(self.piped_API_domains)-1): 
                    self.piped_API_domain_index = 0 
                self.logMessage(f"Trying {self.piped_API_domain_index}: {self.piped_API_domains[self.piped_API_domain_index]}")
                if channel_id[0] == '@':
                    channel_url = self.piped_API_domains[self.piped_API_domain_index]+"/c/"+channel_id
                else:
                    channel_url = self.piped_API_domains[self.piped_API_domain_index]+"/channel/"+channel_id
                response = requests.get(channel_url)

            self.logMessage(f"API used for Channel update: {self.piped_API_domains[self.piped_API_domain_index]} / {self.piped_API_domain_index}")
            json = response.json()
            return json

        except Exception as e:
            self.logMessage(f"Update getChannelDataJSONfromPipedAPI ERROR for vid {channel_id} E: {e}")
            self.piped_API_domain_index += 1
            return self.getChannelDataJSONfromPipedAPI(channel_id)
