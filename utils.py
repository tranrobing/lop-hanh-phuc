import datetime
import pytz

def get_vietnam_time():
    vietnam_tz = pytz.timezone('Asia/Ho_Chi_Minh')
    return datetime.datetime.now(vietnam_tz)
