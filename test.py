import json, datetime
import base64

datetime_str = "12:00"
# Start today at the given time
datetime_obj = datetime.datetime.strptime(datetime_str, "%H:%M")
datetime_obj = datetime_obj.replace(
    year=datetime.datetime.now().year,
    month=datetime.datetime.now().month,
    day=datetime.datetime.now().day,
)
print(datetime_obj)