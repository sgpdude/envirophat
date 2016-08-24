#!/usr/bin/python
"""
enviro.py
Read various Envirophat sensors connected to RPi and publish results to MQTT for use in OpenHab server &
Thingspeak for web access

Aug 21, 2016 Rev 0.0 Early code


To execute: sudo python enviro.py [logfile]
Sensors are read at 5 minute intervals at x:00, x:05 ... and published to MQTT.
Logging to a local file is optional
Requires interface files: 

Known Bugs:

Author: David Oh 
"""
import paho.mqtt.client as mqtt				# MQTT Client API
import time, os, datetime, sys, getopt
import RPi.GPIO as GPIO
from envirophat import light, weather, motion, analog
import logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')


global verbose, log, logfile

MQTTBROKER = "192.168.1.2"					# Use "192.168.1.2" for DS411, "localhost" self explainatory
CLIENTID = "pi0"							# MQTT ID
MQTTUSER = "user"							# Place holders.  Change as appropriate
MQTTPWD = "secret"
numReadings = 4								# Number of readings to take for an average

logfile = ''
verbose = False                                                                                                                        
log = False									# Set to True for troubleshooting only

def main(argv):

	global verbose, log, logfile
	try:
		opts, args = getopt.getopt(argv,"vho:",["ofile="])
	except getopt.GetoptError:
		print 'enviro.py [-v] [-o <outputfile>]'
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print 'enviro.py [-v] [-o <outputfile>]'
			sys.exit()
		elif opt == "-v":
			verbose = True	
		elif opt in ("-o", "--ofile"):
			logfile = arg
			log = True
	if verbose:
		print 'Output file is "%s"' % (logfile)
		print 'verbose =', verbose
		print "log =", log
   
def publish(topic, value, unit):	# Displays the topic/value to be published if verbose mode is set & publishes to MQTT
	if verbose:
		print topic + " " + str(value) + " " + unit
	client.publish(topic, str(value))	

def on_publish(client, userdata, mid):
    if verbose:
		print("Published with result code "+ str(mid))	
	
def cTof(temp):						# Convert temps that are usually returned in C to F
	return((temp * 9.0 / 5.0) + 32.0)
	
if __name__ == "__main__":
	main(sys.argv[1:])
	logging.info('%s started', sys.argv[0])
	if verbose:
		print sys.argv[0],": 5 min interval"
		print "Number of samples to average:", numReadings
	
	if log:
		try:
			file = open(logfile, 'a')
		except IOError:
			print "Could not open:", logfile
			exit(1)
		if verbose:
			print "Opened in append mode:", logfile

	base_date = datetime.datetime(1970,1,1)
	now = datetime.datetime.now()
	target = int((now-base_date).total_seconds())
	target = ((target + 299) / 300) * 300		# Round up to next 5 minute boundary
	if verbose:
		now = datetime.datetime.now()
		now_seconds = int((now-base_date).total_seconds())		
		print "Next reading in ~" + str(target - now_seconds) + " seconds"
	client = mqtt.Client(CLIENTID)
	client.username_pw_set (MQTTUSER, MQTTPWD)
	client.on_publish = on_publish
	client.connect(MQTTBROKER, 1883, 60)
	client.loop_start()								# Start thread that ensures that MQTT is able to send/receive async
	
	while True:
		# Get current datetime
		now = datetime.datetime.now()
		now_seconds = int((now-base_date).total_seconds())
		if now_seconds >= target:
			timeStamp = "%d-%02d-%02d %02d:%02d" % (now.year, now.month, now.day, now.hour, now.minute)
					
			temperature = 0
			pressure = 0
			lightlevel = 0
			r = 0
			g = 0
			b = 0
			heading = 0
			
			try:
				for loop in range(numReadings):
					rgb = light.rgb()
					analog_values = analog.read_all()

					r += rgb[0]
					g += rgb[1]
					b += rgb[2]
					t = cTof(weather.temperature())
					temperature += t
					p = weather.pressure()
					pressure += p
					c = light.light()
					lightlevel += c
					h = motion.heading()
					heading += h
					#a0 = analog_values[0],
					#a1 = analog_values[1],
					#a2 = analog_values[2],
					#a3 = analog_values[3]
					time.sleep(0.1)
					
			except KeyboardInterrupt:
				pass
			temperature /= numReadings
			pressure /= numReadings
			lightlevel /= numReadings
			r /= numReadings
			g /= numReadings
			b /= numReadings
			heading /= numReadings			

			logRecord = "%s,%d,%d,%d,%d,%.1f,%.1f,%.1f" % (timeStamp, lightlevel, r, g, b, temperature, pressure, heading)

			publish("pi0/lightlevel", "%d" % (lightlevel), "Lux")
			publish("pi0/pressure", "%.1f" % (pressure), "hPa")
			publish("pi0/temperature", "%.1f" % (temperature), "F")
			publish("pi0/heading", "%.1f"% heading, "degrees")	
			publish("pi0/red", "%d" % (r), "R")
			publish("pi0/green", "%d" % (g), "G")	
			publish("pi0/blue", "%d" % (b), "B")			
		
			#client.disconnect()
			if verbose:
				print logRecord
				print
			if log:
				print >>file, logRecord
				file.flush()
				os.fsync(file)

			target += 300 # Advance target by 5 minutes		
		time.sleep (20)