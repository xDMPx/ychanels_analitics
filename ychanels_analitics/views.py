from django.shortcuts import render
from django.http import HttpResponse
from django.http import HttpResponseRedirect
from django.http import FileResponse
from django.template import loader
from django.utils import timezone

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from PIL import Image

import pandas as pd
import plotly.express as px
from plotly.offline import plot
import plotly.graph_objects as go
import plotly.io as pio


from .models import Video, Analytics, Channel, ChannelAnalytics
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

import time
import logging
import io

from .forms import AddVideoForm, HistoricalDataDayForm
from .management.commands.scheduler_job import SchedulerJob

from dataclasses import dataclass
@dataclass
class AnalyticsData:
    title: str
    plots: list

def processVideoData(video: Video,start_date: datetime = None,end_date: datetime = None):
    title = video.title
    time_stamps = []
    view_counts = []
    likes_counts = []
    dislikes_counts = []
    comment_counts = []
   
    analytics_data = None
    if start_date == None and end_date == None: 
        analytics_data = Analytics.objects.filter(video=video)
    else:
        analytics_data = Analytics.objects.filter(video=video,time_stamp__range=(start_date,end_date))

    for data in analytics_data:
        time_stamps.append(timezone.localtime(data.time_stamp))
        view_counts.append(data.view_count)
        likes_counts.append(data.likes_count)
        dislikes_counts.append(data.dislikes_count)
        comment_counts.append(data.comment_count)

    plots = []

    dracula_template = pio.templates["plotly_dark"]
    #print(dracula_template.layout)
    dracula_template.layout.font.color = "#80FFEA"
    dracula_template.layout.font.family = "Fira Code, monospace"
    dracula_template.layout.title.pop("x")
    dracula_template.layout.plot_bgcolor="#1d1e26"
    dracula_template.layout.paper_bgcolor="#1d1e26"

    view_count_fig = px.line(x=time_stamps,y=view_counts,title="View count:",markers=True, color_discrete_sequence=["#8AFF80"], template=dracula_template)
    view_count_plot = plot(view_count_fig, output_type="div")
    plots.append(view_count_plot)
    
    likes_count_fig = px.line(x=time_stamps,y=likes_counts,title="Like count:",markers=True, color_discrete_sequence=["rgb(255, 202, 128)"], template=dracula_template)
    likes_count_plot = plot(likes_count_fig, output_type="div")
    plots.append(likes_count_plot)

    dislikes_count_fig = px.line(x=time_stamps,y=dislikes_counts,title="Dislike count:",markers=True, color_discrete_sequence=["rgb(255, 128, 191)"], template=dracula_template)
    dislikes_count_plot = plot(dislikes_count_fig, output_type="div")
    plots.append(dislikes_count_plot)

    comment_count_fig = px.line(x=time_stamps,y=comment_counts,title="Comment count:",markers=True, color_discrete_sequence=["rgb(255, 149, 128)"], template=dracula_template)
    comment_count_plot = plot(comment_count_fig, output_type="div")
    plots.append(comment_count_plot)

    
    a_data = AnalyticsData(video.title, plots)
    return a_data

def processChannelData(channel: Channel,start_date: datetime = None,end_date: datetime = None):
    time_stamps = []
    subscriber_counts = []
   
    analytics_data = None
    if start_date == None and end_date == None: 
        analytics_data = ChannelAnalytics.objects.filter(channel=channel)
    else:
        analytics_data = ChannelAnalytics.objects.filter(channel=channel, time_stamp__range=(start_date,end_date))

    for data in analytics_data:
        time_stamps.append(timezone.localtime(data.time_stamp))
        subscriber_counts.append(data.subscriber_count)

    plots = []

    dracula_template = pio.templates["plotly_dark"]
    dracula_template.layout.font.color = "#80FFEA"
    dracula_template.layout.font.family = "Fira Code, monospace"
    dracula_template.layout.title.pop("x")
    dracula_template.layout.plot_bgcolor="#1d1e26"
    dracula_template.layout.paper_bgcolor="#1d1e26"

    subscriber_count_fig = px.line(x=time_stamps,y=subscriber_counts,title="Subscriber count:",markers=True, color_discrete_sequence=["#8AFF80"], template=dracula_template)
    subscriber_count_plot = plot(subscriber_count_fig, output_type="div")
    plots.append(subscriber_count_plot)
    
    a_data = AnalyticsData(str(channel.name), plots)
    return a_data


# Create your views here.
def index(request):
    template = loader.get_template("index.html")
    
    scheduler_job = SchedulerJob()
    
    # get the start time
    st = time.time() 


    vids_data = []
    videos = Video.objects.filter(channel=None)
    for video in videos:
        vids_data.append({"title": video.title, "video_id": video.video_id })
    
    channels = Channel.objects.all()
    channels_data = []
    for channel in channels:
        channels_data.append({'channel_name': channel.name, 'channel_id': channel.channel_id })

    context = {
        'vids_data': vids_data,
        'channels_data': channels_data
    }

    if request.method == 'POST':
        form = AddVideoForm(request.POST)
        if form.is_valid():
            if form.cleaned_data['video_or_channel_id'] == '1':
                video_id = form.cleaned_data['id']
                title = scheduler_job.getVideoDataJSONfromPipedAPI(video_id)['title']
                Video(video_id=video_id,title=title).save()
                scheduler_job.initializeAnalytics(video_id)
                return HttpResponseRedirect('')
            else:
                channel_id = form.cleaned_data['id']
                json = scheduler_job.getChannelDataJSONfromPipedAPI(channel_id)
                channel = Channel(channel_id=json['id'],name=json['name'])
                channel.save()
                now = timezone.localtime(timezone.now())
                ChannelAnalytics(channel=channel,subscriber_count=json['subscriberCount'],time_stamp=now).save()
                vid_json = json["relatedStreams"][0]
                video_id = vid_json['url'].split("v=")[1]
                title = vid_json['title']
                Video(video_id=video_id,title=title,channel=channel).save()
                scheduler_job.initializeAnalytics(video_id)
                return HttpResponseRedirect('')

            
    form = AddVideoForm()
    context['form'] = form 
    
    # get the end time
    et = time.time()
    # get the execution time
    elapsed_time = et - st
    logging.info(f'Execution time INDEX: {elapsed_time} seconds')
   
    return HttpResponse(template.render(context, request))

    

def videos(request, video_id):

    if request.method == 'POST':
        form = HistoricalDataDayForm(request.POST)
        if form.is_valid():
            year =  form.cleaned_data['date'].year
            month = form.cleaned_data['date'].month
            day = form.cleaned_data['date'].day
            return HttpResponseRedirect(f'/videos-historical/{video_id}/{year}/{month}/{day}')
    
    # get the start time
    st = time.time()
    
    video = Video.objects.get(video_id=video_id)
    template = loader.get_template("videos.html")
    
    
    current_time = timezone.localtime(timezone.now())
    # day
    start_date = current_time-timedelta(hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data = [processVideoData(video,start_date,end_date)]
    # week
    start_date = current_time-timedelta(days=current_time.weekday(),hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data.append(processVideoData(video,start_date,end_date))
    
    # month
    start_date = current_time-timedelta(days=current_time.day-1,hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data.append(processVideoData(video,start_date,end_date))
    
    context = {
        'data': data,
        'title': video.title,
        'video_id': video_id,
        'year': current_time.year,
        'month': current_time.month,
        'day': current_time.day
    }


    first_analytics = Analytics.objects.filter(video=video).first()
    form = HistoricalDataDayForm()
    context['form'] = form 
    context['form_start_date'] = f"{first_analytics.time_stamp.year}-{first_analytics.time_stamp.month}-{first_analytics.time_stamp.day}"
    

    # get the end time
    et = time.time()
    # get the execution time
    elapsed_time = et - st
    logging.info(f'{video_id}')

    logging.info(f'Execution time VIDEOS: {elapsed_time} seconds')
   
    return HttpResponse(template.render(context, request))

 
def videos_historical(request, video_id, year, month, day):

    if request.method == 'POST':
        form = HistoricalDataDayForm(request.POST)
        if form.is_valid():
            year =  form.cleaned_data['date'].year
            month = form.cleaned_data['date'].month
            day = form.cleaned_data['date'].day
            return HttpResponseRedirect(f'/videos-historical/{video_id}/{year}/{month}/{day}')
    
    # get the start time
    st = time.time()
    
    video = Video.objects.get(video_id=video_id)
    template = loader.get_template("videos.html")
    
    
    current_time = datetime(year=year,month=month,day=day,hour=23,minute=59,second=59,tzinfo=timezone.get_current_timezone())
    # day
    start_date = current_time-timedelta(hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data = [processVideoData(video,start_date,end_date)]
    # week
    current_time = current_time+timedelta(days=6-current_time.weekday())
    start_date = current_time-timedelta(days=current_time.weekday(),hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    print(f"week start: {start_date} end: {end_date}")
    data.append(processVideoData(video,start_date,end_date))
    
    # month
    current_time = current_time+relativedelta(day=31)
    start_date = current_time-timedelta(days=current_time.day-1,hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    print(f"month start: {start_date} end: {end_date}")
    data.append(processVideoData(video,start_date,end_date))
    
    context = {
        'data': data,
        'title': video.title,
        'video_id': video_id,
        'year': year,
        'month': month,
        'day': day
    }


    first_analytics = Analytics.objects.filter(video=video).first()
    form = HistoricalDataDayForm()
    context['form'] = form 
    context['form_start_date'] = f"{first_analytics.time_stamp.year}-{first_analytics.time_stamp.month}-{first_analytics.time_stamp.day}"
    

    # get the end time
    et = time.time()
    # get the execution time
    elapsed_time = et - st
    logging.info(f'{video_id}')

    logging.info(f'Execution time VIDEOS: {elapsed_time} seconds')
   
    return HttpResponse(template.render(context, request))

def channels_historical(request, channel_id, year, month, day):
    
    if request.method == 'POST':
        form = HistoricalDataDayForm(request.POST)
        if form.is_valid():
            year =  form.cleaned_data['date'].year
            month = form.cleaned_data['date'].month
            day = form.cleaned_data['date'].day
            return HttpResponseRedirect(f'/channels-historical/{channel_id}/{year}/{month}/{day}')
      
    # get the start time
    st = time.time()
    
    template = loader.get_template("channels.html")

    channel = Channel.objects.get(channel_id=channel_id)
    
    channel_videos = Video.objects.filter(channel=channel)
    channel_videos_data = []
    for video in channel_videos:
            channel_videos_data.append({"title": video.title, "video_id": video.video_id })

    channel_data = {'channel_name': channel.name, 'channel_videos_data': channel_videos_data}

    current_time = datetime(year=year,month=month,day=day,hour=23,minute=59,second=59,tzinfo=timezone.get_current_timezone())
    # day
    start_date = current_time-timedelta(hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data = [processChannelData(channel,start_date,end_date)]
    # week
    current_time = current_time+timedelta(days=6-current_time.weekday())
    start_date = current_time-timedelta(days=current_time.weekday(),hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    print(f"week start: {start_date} end: {end_date}")
    data.append(processChannelData(channel,start_date,end_date))
    
    # month
    current_time = current_time+relativedelta(day=31)
    start_date = current_time-timedelta(days=current_time.day-1,hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    print(f"month start: {start_date} end: {end_date}")
    data.append(processChannelData(channel,start_date,end_date))
    

    context = {
        'channel_data': channel_data,
        'analytics_data': data,
        'channel_id': channel_id,
        'year': year,
        'month': month,
        'day': day
    }
    
    first_analytics = ChannelAnalytics.objects.filter(channel=channel).first()
    form = HistoricalDataDayForm()
    context['form'] = form 
    context['form_start_date'] = f"{first_analytics.time_stamp.year}-{first_analytics.time_stamp.month}-{first_analytics.time_stamp.day}"
    
    
    # get the end time
    et = time.time()
    # get the execution time
    elapsed_time = et - st

    logging.info(f'Execution time VIDEOS: {elapsed_time} seconds')
   
    return HttpResponse(template.render(context, request))


def channels(request, channel_id):

    if request.method == 'POST':
        form = HistoricalDataDayForm(request.POST)
        if form.is_valid():
            year =  form.cleaned_data['date'].year
            month = form.cleaned_data['date'].month
            day = form.cleaned_data['date'].day
            return HttpResponseRedirect(f'/channels-historical/{channel_id}/{year}/{month}/{day}')

    # get the start time
    st = time.time()
    
    template = loader.get_template("channels.html")

    channel = Channel.objects.get(channel_id=channel_id)
    
    channel_videos = Video.objects.filter(channel=channel)
    channel_videos_data = []
    for video in channel_videos:
            channel_videos_data.append({"title": video.title, "video_id": video.video_id })

    channel_data = {'channel_name': channel.name, 'channel_videos_data': channel_videos_data}

    current_time = timezone.localtime(timezone.now())
    # day
    start_date = current_time-timedelta(hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data = [processChannelData(channel,start_date,end_date)]
    # week
    start_date = current_time-timedelta(days=current_time.weekday(),hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data.append(processChannelData(channel,start_date,end_date))
    
    # month
    start_date = current_time-timedelta(days=current_time.day-1,hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data.append(processChannelData(channel,start_date,end_date))
    

    context = {
        'channel_data': channel_data,
        'analytics_data': data,
        'channel_id': channel_id,
        'year': current_time.year,
        'month': current_time.month,
        'day': current_time.day
    }
    
    first_analytics = ChannelAnalytics.objects.filter(channel=channel).first()
    form = HistoricalDataDayForm()
    context['form'] = form 
    context['form_start_date'] = f"{first_analytics.time_stamp.year}-{first_analytics.time_stamp.month}-{first_analytics.time_stamp.day}"
    
    
    # get the end time
    et = time.time()
    # get the execution time
    elapsed_time = et - st

    logging.info(f'Execution time VIDEOS: {elapsed_time} seconds')
   
    return HttpResponse(template.render(context, request))

def processVideoDataPDF(video: Video,start_date: datetime = None,end_date: datetime = None):
    title = video.title
    time_stamps = []
    view_counts = []
    likes_counts = []
    dislikes_counts = []
    comment_counts = []
   
    analytics_data = None
    if start_date == None and end_date == None: 
        analytics_data = Analytics.objects.filter(video=video)
    else:
        analytics_data = Analytics.objects.filter(video=video,time_stamp__range=(start_date,end_date))

    for data in analytics_data:
        time_stamps.append(timezone.localtime(data.time_stamp))
        view_counts.append(data.view_count)
        likes_counts.append(data.likes_count)
        dislikes_counts.append(data.dislikes_count)
        comment_counts.append(data.comment_count)

    plots = []

    view_count_fig = px.line(x=time_stamps,y=view_counts,title="View count:",markers=True)
    view_count_plot = pio.to_image(view_count_fig, format="png")
    plots.append(view_count_plot)
    
    likes_count_fig = px.line(x=time_stamps,y=likes_counts,title="Like count:",markers=True)
    likes_count_plot = pio.to_image(likes_count_fig, format="png")
    plots.append(likes_count_plot)

    dislikes_count_fig = px.line(x=time_stamps,y=dislikes_counts,title="Dislike count:",markers=True)
    dislikes_count_plot = pio.to_image(dislikes_count_fig, format="png")
    plots.append(dislikes_count_plot)

    comment_count_fig = px.line(x=time_stamps,y=comment_counts,title="Comment count:",markers=True)
    comment_count_plot = pio.to_image(comment_count_fig, format="png")
    plots.append(comment_count_plot)

    return plots

def processChannelDataPDF(channel: Channel,start_date: datetime = None,end_date: datetime = None):
    time_stamps = []
    subscriber_counts = []
   
    analytics_data = None
    if start_date == None and end_date == None: 
        analytics_data = ChannelAnalytics.objects.filter(channel=channel)
    else:
        analytics_data = ChannelAnalytics.objects.filter(channel=channel, time_stamp__range=(start_date,end_date))

    for data in analytics_data:
        time_stamps.append(timezone.localtime(data.time_stamp))
        subscriber_counts.append(data.subscriber_count)

    plots = []

    subscriber_count_fig = px.line(x=time_stamps,y=subscriber_counts,title="Subscriber count:",markers=True)
    subscriber_count_plot = pio.to_image(subscriber_count_fig, format="png")
    plots.append(subscriber_count_plot)
    
    return plots

def download_channel_pdf(request, channel_id, year, month, day):
    
    channel = Channel.objects.get(channel_id=channel_id)

    # Create a file-like buffer to receive PDF data.
    buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer,pagesize=A4)


    title_text = f"{channel.name}"
    h1_fs = 18
    x = 50
    y = 750
    # Draw the heading text onto the canvas
    max_ch_in_line = 45
    p.setFont("Courier-Bold", h1_fs)
    if len(title_text) > max_ch_in_line:
        title_text = title_text.split(' ')
        text = ''
        for word in title_text:
            if len(text)+len(word) < (1+text.count('\n'))*max_ch_in_line:
                text+=f" {word}"
            else:
                text+=f"\n {word}"
        for texts in text.split('\n'):
            p.drawString(x=x, y=y,text=texts)
            y -= 2*h1_fs     
    else:
        p.drawString(x=x, y=y,text=title_text)
    
    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    current_time = datetime(year=year,month=month,day=day,hour=23,minute=59,second=59,tzinfo=timezone.get_current_timezone())
    # day
    heading_day = "Day: "
    y -= 2*h1_fs
    h2_fs = 14
    # Set the font size and font style for the heading 2
    p.setFont("Courier", h2_fs)
    p.drawString(x=x, y=y, text=heading_day)

    start_date = current_time-timedelta(hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data = processChannelDataPDF(channel,start_date,end_date)
    img_height = 300
    # Draw the graph image onto the canvas
    for plot_img in data:
        y -= 2*h2_fs+img_height
        if y < 0:
            y = 750
            y -= 2*h2_fs+img_height
            p.showPage() 
        buffer_img = io.BytesIO()
        buffer_img.write(plot_img)
        buffer_img.seek(0)
        image = ImageReader(buffer_img)
        p.drawImage(image, x=x, y=y, width=500, height=img_height)

    p.showPage() 
    y = 750

    # week
    heading_day = "Week: "
    y -= 2*h1_fs
    h2_fs = 14
    # Set the font size and font style for the heading 2
    p.setFont("Courier", h2_fs)
    p.drawString(x=x, y=y, text=heading_day)

    current_time = current_time+timedelta(days=6-current_time.weekday())
    start_date = current_time-timedelta(days=current_time.weekday(),hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data = processChannelDataPDF(channel,start_date,end_date)
    # Draw the graph image onto the canvas
    for plot_img in data:
        y -= 2*h2_fs+img_height
        if y < 0:
            y = 750
            y -= 2*h2_fs+img_height
            p.showPage() 
        buffer_img = io.BytesIO()
        buffer_img.write(plot_img)
        buffer_img.seek(0)
        image = ImageReader(buffer_img)
        p.drawImage(image, x=x, y=y, width=500, height=img_height)

    p.showPage() 
    y = 750

    # month
    heading_day = "Month: "
    y -= 2*h1_fs
    h2_fs = 14
    # Set the font size and font style for the heading 2
    p.setFont("Courier", h2_fs)
    p.drawString(x=x, y=y, text=heading_day)

    current_time = current_time+relativedelta(day=31)
    start_date = current_time-timedelta(days=current_time.day-1,hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data = processChannelDataPDF(channel,start_date,end_date)
    
    # Draw the graph image onto the canvas
    for plot_img in data:
        y -= 2*h2_fs+img_height
        if y < 0:
            y = 750
            y -= 2*h2_fs+img_height
            p.showPage() 
        buffer_img = io.BytesIO()
        buffer_img.write(plot_img)
        buffer_img.seek(0)
        image = ImageReader(buffer_img)
        p.drawImage(image, x=x, y=y, width=500, height=img_height)
        
    p.showPage() 


    # Close the PDF object cleanly, and we're done.
    p.save()

    # FileResponse sets the Content-Disposition header so that browsers
    # present the option to save the file.
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='hello.pdf')

def download_video_pdf(request, video_id, year, month, day):
    
    video = Video.objects.get(video_id=video_id)

    # Create a file-like buffer to receive PDF data.
    buffer = io.BytesIO()

    # Create the PDF object, using the buffer as its "file."
    p = canvas.Canvas(buffer,pagesize=A4)


    title_text = f"{video.title}"
    h1_fs = 18
    x = 50
    y = 750
    # Draw the heading text onto the canvas
    max_ch_in_line = 45
    p.setFont("Courier-Bold", h1_fs)
    if len(title_text) > max_ch_in_line:
        title_text = title_text.split(' ')
        text = ''
        for word in title_text:
            if len(text)+len(word) < (1+text.count('\n'))*max_ch_in_line:
                text+=f" {word}"
            else:
                text+=f"\n {word}"
        for texts in text.split('\n'):
            p.drawString(x=x, y=y,text=texts)
            y -= 2*h1_fs     
    else:
        p.drawString(x=x, y=y,text=title_text)
    
    # Draw things on the PDF. Here's where the PDF generation happens.
    # See the ReportLab documentation for the full list of functionality.
    
    current_time = datetime(year=year,month=month,day=day,hour=23,minute=59,second=59,tzinfo=timezone.get_current_timezone())
    # day
    heading_day = "Day: "
    y -= 2*h1_fs
    h2_fs = 14
    # Set the font size and font style for the heading 2
    p.setFont("Courier", h2_fs)
    p.drawString(x=x, y=y, text=heading_day)

    start_date = current_time-timedelta(hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data = processVideoDataPDF(video,start_date,end_date)
    img_height = 300
    # Draw the graph image onto the canvas
    for plot_img in data:
        y -= 2*h2_fs+img_height
        if y < 0:
            y = 750
            y -= 2*h2_fs+img_height
            p.showPage() 
        buffer_img = io.BytesIO()
        buffer_img.write(plot_img)
        buffer_img.seek(0)
        image = ImageReader(buffer_img)
        p.drawImage(image, x=x, y=y, width=500, height=img_height)

    p.showPage() 
    y = 750

    # week
    heading_day = "Week: "
    y -= 2*h1_fs
    h2_fs = 14
    # Set the font size and font style for the heading 2
    p.setFont("Courier", h2_fs)
    p.drawString(x=x, y=y, text=heading_day)

    current_time = current_time+timedelta(days=6-current_time.weekday())
    start_date = current_time-timedelta(days=current_time.weekday(),hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data = processVideoDataPDF(video,start_date,end_date)
    # Draw the graph image onto the canvas
    for plot_img in data:
        y -= 2*h2_fs+img_height
        if y < 0:
            y = 750
            y -= 2*h2_fs+img_height
            p.showPage() 
        buffer_img = io.BytesIO()
        buffer_img.write(plot_img)
        buffer_img.seek(0)
        image = ImageReader(buffer_img)
        p.drawImage(image, x=x, y=y, width=500, height=img_height)

    p.showPage() 
    y = 750

    # month
    heading_day = "Month: "
    y -= 2*h1_fs
    h2_fs = 14
    # Set the font size and font style for the heading 2
    p.setFont("Courier", h2_fs)
    p.drawString(x=x, y=y, text=heading_day)

    current_time = current_time+relativedelta(day=31)
    start_date = current_time-timedelta(days=current_time.day-1,hours=current_time.hour,minutes=current_time.minute,seconds=current_time.second)
    end_date = current_time
    data = processVideoDataPDF(video,start_date,end_date)
    
    # Draw the graph image onto the canvas
    for plot_img in data:
        y -= 2*h2_fs+img_height
        if y < 0:
            y = 750
            y -= 2*h2_fs+img_height
            p.showPage() 
        buffer_img = io.BytesIO()
        buffer_img.write(plot_img)
        buffer_img.seek(0)
        image = ImageReader(buffer_img)
        p.drawImage(image, x=x, y=y, width=500, height=img_height)
        
    p.showPage() 


    # Close the PDF object cleanly, and we're done.
    p.save()

    # FileResponse sets the Content-Disposition header so that browsers
    # present the option to save the file.
    buffer.seek(0)
    return FileResponse(buffer, as_attachment=True, filename='hello.pdf')



