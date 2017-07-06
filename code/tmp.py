from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta
import time
import sys
scheduler = BackgroundScheduler()

scheduler.start()

# Define the function that is to be executed
def my_job(text):
	print ""
	print text 

offset=10
exec_date = (datetime.now() + timedelta(seconds=offset)).time()
#from ipdb import set_trace; set_trace()
job = scheduler.add_job(my_job, args=['yeah brah, redonculous'],trigger='cron', second=1)

print "[{}]".format(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
while True:
	sys.stdout.write("\r"+datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
	sys.stdout.flush()
	time.sleep(1)
