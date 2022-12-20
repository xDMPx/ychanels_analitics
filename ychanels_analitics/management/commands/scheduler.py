import logging

from django.conf import settings

from apscheduler.schedulers.background import BlockingScheduler 
from apscheduler.triggers.cron import CronTrigger
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util
from django.core.management.base import BaseCommand


from .scheduler_job import SchedulerJob
import apscheduler.events

# The `close_old_connections` decorator ensures that database connections, that have become
# unusable or are obsolete, are closed before and after your job has run. You should use it
# to wrap any jobs that you schedule that access the Django database in any way. 
@util.close_old_connections
def delete_old_job_executions(max_age=604_800):
  """
  This job deletes APScheduler job execution entries older than `max_age` from the database.
  It helps to prevent the database from filling up with old historical records that are no
  longer useful.
  
  :param max_age: The maximum length of time to retain historical job execution records.
                  Defaults to 7 days.
  """
  DjangoJobExecution.objects.delete_old_job_executions(max_age)


def my_listener(event):
    if event.exception:
        logging.info(f'The job crashed :( {event.exception.message}')
    else:
        logging.info('The job worked :)')

class Command(BaseCommand):
    help = "Runs APScheduler."

    def handle(self, *args, **options):
        scheduler_job = SchedulerJob()
        scheduler_job.logMessage("Django Project started") 


        if settings.DEBUG:
      	    # Hook into the apscheduler logger
            logging.basicConfig(level=logging.DEBUG)
            logging.getLogger('apscheduler').setLevel(logging.DEBUG)

    # - Execute jobs in threads inside the application process
    #SCHEDULER_CONFIG = {
    #    'apscheduler.executors.processpool': {
    #        "type": "threadpool"
    #    },
    #}
    # - Execute jobs in threads inside the application process
    #scheduler = BlockingScheduler(SCHEDULER_CONFIG,timezone=settings.TIME_ZONE)
        scheduler = BlockingScheduler(timezone=settings.TIME_ZONE)
        scheduler.add_jobstore(DjangoJobStore(), "default")
        DjangoJobStore().remove_all_jobs() 
    
    #scheduler.add_job(sendMessage, 'cron', hour="*", minute="0", args=("cron Hourly",))
        scheduler.add_job(scheduler_job.updateData, 'cron', hour="*", minute="0/15", misfire_grace_time=600) 
    
        scheduler.add_job(
            delete_old_job_executions,
            trigger=CronTrigger(
            day_of_week="mon", hour="00", minute="00"
            ),  # Midnight on Monday, before start of the next work week.
            id="delete_old_job_executions",
            max_instances=1,
            replace_existing=True,
            )
        logging.info(
            "Added weekly job: 'delete_old_job_executions'."
        )

        scheduler.add_listener(my_listener, apscheduler.events.EVENT_JOB_MAX_INSTANCES)
        logging.info("Starting scheduler...")
        scheduler.start()
        #updateData()
    

        #except KeyboardInterrupt:
        #  logger.info("Stopping scheduler...")
        #  scheduler.shutdown()
        #  logger.info("Scheduler shut down successfully!")
