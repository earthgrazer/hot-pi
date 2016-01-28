import sqlite3
import json
import datetime
import time
import logging
import logging.config
from flask import Flask
from flask import g
from flask import Response
from flask import request

application = Flask(__name__)

logging.config.fileConfig("logging.conf")
logger = logging.getLogger()

DATABASE = "/opt/hotpiweb/temperatures.db"

EPOCH = datetime.datetime(1970, 1, 1)

def get_db():
	db = getattr(g, "_database", None)
	if db is None:
		db = g._database = connect_to_database()
	return db

def connect_to_database():
	return sqlite3.connect(DATABASE)
	
@application.teardown_appcontext
def close_connection(exception):
	db = getattr(g, "_database", None)
	if db is not None:
		db.close()

""" Handler for temperature queries.

/api/temperatures?start=<start_time>&end=<end_time>&interval=<interval>&minus=<minus>

Parameters:
	start_time = query start time in seconds since epoch
	end_time = query end time in seconds since epoch
	interval = averaging interval in seconds
	minus = seconds before current time to start querying
"""
@application.route("/api/temperatures", methods=["GET"])	
def temperatures():
	# to compute query execution time
	reqStartTime = time.time()
	
	""" Query parameters default to one day before current time,
	for the duration of one day, and averaging interval of
	half an hour
	"""
	minusTime = datetime.timedelta(days=1)
	end = datetime.datetime.utcnow()
	start = end - minusTime
	interval = 1800
	resp = {"stats": {"executionElapsedTime": 0, "recordsRetrieved": 0}, "temperatures":[]}

	logger.debug("request url: " + str(request.url))

	if request.args.has_key("start"):
		requestStart = datetime.datetime.utcfromtimestamp(int(request.args.get("start")))
	else:
		requestStart = start
	if request.args.has_key("end"):
		requestEnd = datetime.datetime.utcfromtimestamp(int(request.args.get("end")))
	else:
		requestEnd = end
	if request.args.has_key("interval"):
		requestInterval = int(request.args.get("interval"))
	else:
		requestInterval = interval
		
	if requestStart <= requestEnd:
		start = requestStart
		end = requestEnd
	
	""" if "minus" param is provided, override given start time
	"""
	if request.args.has_key("minus") and int(request.args.get("minus")) > 0:
		minus = datetime.timedelta(seconds=int(request.args.get("minus")))
		start = end - minus
	
	if requestInterval > 0:
		interval = requestInterval
	
	start = int((start - EPOCH).total_seconds())
	end = int((end - EPOCH).total_seconds())
	interval = min(end - start, interval)
	
	logger.debug("start: " + str(start) + ", end: " + str(end))
	
	conn = get_db()
	c = conn.cursor()
	c.execute('select cast(strftime("%s", timestamp) as int), temperature from temperatures where timestamp between datetime(?, "unixepoch") and datetime(?, "unixepoch");', (start, end))
	
	currIntervalStart = start
	currIntervalEnd = start + interval
	row = None
	
	""" Calculate the average temperature in each interval.
	If an interval has no temperature records, then an average
	of zero is used for the interval.
	"""
	while currIntervalStart <= end:
		n = delta = mean = 0.0
		hasValue = False;
	
		while True:
			if row != None:
				if row[0] < currIntervalEnd:
					hasValue = True
					n, delta, mean = calc_mean(n, delta, mean, row[1])
					row = c.fetchone()
				else:
					break
			else:
				row = c.fetchone()
				if row == None:
					break
	
		if hasValue:
			resp["temperatures"].append({"d": int(currIntervalStart), "t": int(mean)})
			resp["stats"]["recordsRetrieved"] += n
		else:
			resp["temperatures"].append({"d": int(currIntervalStart), "t": None})
		currIntervalStart = currIntervalEnd
		currIntervalEnd = currIntervalEnd + interval
	
	resp["stats"]["executionElapsedTime"] = time.time() - reqStartTime
	
	return Response(json.dumps(resp), mimetype="application/json")

""" Online mean function.
"""
def calc_mean(n, delta, mean, curr):
	n = n + 1
	delta = curr - mean
	mean = mean + delta / n
	return n, delta, mean
		

if __name__ == "__main__":
	application.run(host="0.0.0.0", debug=True)
