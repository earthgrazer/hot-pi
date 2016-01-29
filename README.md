# hot-pi
Raspberry Pi CPU temperature recording and visualization.

## Components
### hotpid
hot-pi daemon to poll CPU temperature on regular interval and write value to database (sqlite).

### hotpiweb
Flask web application that queries the database for temperature values over time and presents the data in visualizations using d3.js.

## Hosting on the Raspberry Pi 2
Use nginx as reverse proxy to forward requests to the web app through WSGI (uwsgi).
