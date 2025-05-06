import datetime

x = datetime.datetime.now().strftime("%H:%M:%S")

print(x)

new_x = datetime.datetime.strptime(x, "%H:%M:%S")

print(new_x)