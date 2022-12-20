from django import forms
from django.utils import timezone

class AddVideoForm(forms.Form):
    video_or_channel_id = forms.ChoiceField(choices=(('1','Video ID'),('2','Channel ID')),label='')
    video_or_channel_id.widget.attrs.update({'class' : 'drac-select drac-select-purple'})
    id = forms.CharField(max_length=255,required=True,label='')
    id.widget.attrs.update({'class' : 'drac-input drac-input-border-sm drac-input-green drac-text-green', 'placeholder' : "ID"})

class HistoricalDataDayForm(forms.Form):
    date = forms.DateField(required=True,initial=timezone.localtime(timezone.now()))
    date.widget.attrs.update({'class' : 'drac-input drac-input-border-sm drac-input-green drac-text-green', 'placeholder' : "Date"})
