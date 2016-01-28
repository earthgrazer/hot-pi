import sqlite3
import threading
import time

class TemperatureRecorder:
	thread_stop_event = threading.Event()
	last_temp = 0
	last_commit_time = time.time()

	def start(self):
		threading.Thread(target=self.record, args=(self.thread_stop_event,)).start()
		
	def stop(self):
		self.thread_stop_event.set()
		
	def record(self, stop_event):
		conn = sqlite3.connect("/opt/temprec/temperatures.db")
		conn.execute("CREATE TABLE IF NOT EXISTS temperatures(timestamp DATETIME DEFAULT CURRENT_TIMESTAMP PRIMARY KEY ASC, temperature INTEGER)")
	
		while (not stop_event.is_set()):
			self.last_temp = self.get_curr_temp()
			conn.execute("INSERT INTO temperatures(temperature) VALUES(" + str(self.last_temp) + ")")
			if time.time() - self.last_commit_time > 60:
				conn.commit()
				self.last_commit_time = time.time()
			stop_event.wait(10)
			
		conn.close()
		
	def get_curr_temp(self):
		with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
			temp = int(f.read())
		
		return temp

recorder = TemperatureRecorder()
recorder.start()
try:
	while (True):
		time.sleep(1)
except KeyboardInterrupt:
	recorder.stop()
recorder.stop()