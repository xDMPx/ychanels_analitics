from django.apps import AppConfig
from django.conf import settings

import sys
import os
import logging

class MyOutput():
    def __init__(self,sys_output, logfile):
        self.stdout = sys_output
        self.log = open(logfile, 'w')
    
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

class YChanelsAnaliticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ychanels_analitics'
    
    def ready(self):
        if 'runserver' in sys.argv and '--noreload' in sys.argv:
            if settings.DEBUG:
                # Hook into the apscheduler logger
                sys.stdout = MyOutput(sys.stdout,"stdout_log")
                sys.stderr = MyOutput(sys.stderr,"stderr_log")
                logging.basicConfig(level=logging.DEBUG)
            if settings.SCHEDULER_AUTOSTART:
                os.chdir(os.path.dirname(__file__))
                os.system("python -u ../manage.py scheduler &")
