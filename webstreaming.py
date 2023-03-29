# import the necessary packages
from pyimagesearch.motion_detection.singlemotiondetector import SingleMotionDetector
from flask import Response
from flask import Flask
from flask import render_template
from flask import request, send_file
from flask import Flask, render_template, redirect, url_for, request, session, flash
import hashlib
from functools import wraps
import threading
import argparse
import datetime
import sys
import time
import cv2
import cryptography
import os
from pathlib import Path


# Initialize the output frame and a lock used to ensure thread-safe
# exchanges of the output frames (useful when multiple browsers/tabs
# are viewing the stream)
outputFrame = None
lock = threading.Lock()
cap = False
global logger
# Initialize a flask object
app = Flask(__name__, template_folder='templateFiles', static_folder='staticFiles')
# Initialize the video stream and allow the camera sensor to warmup by sleeping
vs = cv2.VideoCapture(0)
time.sleep(2.0)
app.secret_key = 'secret_key'

# Decorator function to verify if user is logged in
def logged_in(f):
    @wraps(f)
    def decorated_func(*args, **kwargs):
        if session.get("logged_in") == True:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('login'))
    return decorated_func

# Route for handling the login page logic
# Password is hashed using MD5 and stored in a file
@app.route('/', methods=['GET', 'POST'])
def login():
	error = None
	if request.method == 'POST':

		auth = (request.form['password']).encode()
		auth_hash = hashlib.md5(auth).hexdigest()
		with open("./video_streamer_website/creds/credentials.txt", "r") as f:
			stored_email, stored_pwd = f.read().split("\n")
		f.close()

		if request.form['username'] == stored_email and auth_hash == stored_pwd:
			session['logged_in'] = True
			return redirect(url_for('index'))			
		else:
			error = 'Invalid Credentials. Please try again.'

	return render_template( "login.html", error=error)

# Route for handling logout logic
@app.route('/logout', methods=['POST'])
@logged_in
def logout():
	session['logged_in'] = False
	return redirect(url_for('login'))

@app.route("/index", methods=['GET', 'POST'])
@logged_in
def index():

	# Allow for user buttons to record the video
	if request.method == 'POST':
		if request.form.get('action1') == 'VALUE1':
			global cap, out
			if cap == False:
				fourcc = cv2.VideoWriter_fourcc(*'mp4v')
				out = cv2.VideoWriter("./video_streamer_website/videos/" + datetime.datetime.now().strftime("%A %d %B %Y") + ".mp4",fourcc, 32, (640,480))
				cap = True
				return render_template( "index.html", rec_state=str(cap))
		elif  request.form.get('action2') == 'VALUE2':
			if cap == True:
				out.release()
				cap = False
			return render_template( "index.html", rec_state=str(cap))
		else:
			cap = False
			return render_template( "index.html", rec_state=str(cap))
	else:
		cap = False
		return render_template( "index.html", rec_state=str(cap))



def detect_motion(frameCount):
	# Grab global references 
	global vs, outputFrame, lock, frame, log
	# Initialize the motion detector 
	md = SingleMotionDetector(accumWeight=0.5)
	total = 0
	log=[""]
	# Loop over frames from the video stream
	while True:
		# Read the next frame from the video stream, resize it,
		# Convert the frame to grayscale, and blur it
		_, frame = vs.read()
		gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
		gray = cv2.GaussianBlur(gray, (7, 7), 0)
		# Grab the current timestamp and draw it on the frame
		timestamp = datetime.datetime.now()
		cv2.putText(frame, timestamp.strftime("%A %d %B %Y %I:%M:%S%p"), (10, frame.shape[0] - 10),
			cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)

		# If there is enough frames received, start processing
		if total > frameCount:
			# Detect motion in the image
			motion = md.detect(gray)
			# Check to see if motion was found in the frame
			if motion is not None:
				(thresh, (minX, minY, maxX, maxY)) = motion
				area = (maxX-minX)*(maxY-minY)
				# If the area is large enough, record its movement and add the box
				if area > 2000:
					cv2.rectangle(frame, (minX, minY), (maxX, maxY),(0, 0, 255), 2)
					if ((timestamp.strftime("%A %d %B %Y %I:%M:%S%p")) not in log[-1]) :
						log_motion(timestamp)

		# Update the background model and increment the total number read thus far
		md.update(gray)
		total += 1
		if cap is True:
			out.write(frame)
		with lock:
			outputFrame = frame.copy()

def generate():
	# Grab global references to the output frame and lock variables
	global outputFrame, lock
	# Loop over frames from the output stream
	while True:
		# Wait until the lock is acquired
		with lock:
			# Check if the output frame is available, otherwise skip
			if outputFrame is None:
				continue
			# Encode the frame in JPG format
			(flag, encodedImage) = cv2.imencode(".jpg", outputFrame)

			# Ensure the frame was successfully encoded
			if not flag:
				continue
		# Generate the output frame in a byte format
		yield(b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + bytearray(encodedImage) + b'\r\n')

# Output the video frames
@app.route("/video_feed")
@logged_in
def video_feed():
	return Response(generate(), mimetype = "multipart/x-mixed-replace; boundary=frame")

# Display movement logs
@app.route("/output_logs", methods=['POST'])
@logged_in
def output_logs():
	logs=log
	logs.reverse()
	output_log=("\n".join(logs))
	return render_template( "index.html", output_log=output_log,rec_state=str(cap) )

@app.route("/download", methods=['POST'])
@logged_in
def download():
	# Download a file after checking it exists
	path = Path("./video_streamer_website/videos/" + datetime.datetime.now().strftime("%A %d %B %Y") + ".mp4")
	if os.path.exists(path):
		return send_file(Path(path), as_attachment=True)
	else:
		return redirect(url_for('index'))

def log_motion(timestamp):
	global logger
	log.append("Motion detected at: " + timestamp.strftime("%A %d %B %Y %I:%M:%S%p"))
	logger = open("./video_streamer_website/logs/"+timestamp.now().strftime("%A %d %B %Y") +".txt","a",encoding='utf-8')
	logger.write("Motion detected at: " + timestamp.strftime("%I:%M:%S%p") +"\n")
	logger.close()


# Check if this is the main thread
if __name__ == '__main__':
	# Construct the argparse to enable IP and port parameters on terminal
	ap = argparse.ArgumentParser()
	ap.add_argument("-f", "--frame-count", type=int, default=32,
		help="# of frames used to construct the background model")
	# start a thread that will perform motion detection
	t = threading.Thread(target=detect_motion, args=(32,))
	t.daemon = True
	t.start()
	# start the flask app
	app.run(host="0.0.0.0", port=8000, debug=True, threaded=True, ssl_context=('./video_streamer_website/creds/cert.pem','./video_streamer_website/creds/key.pem'),use_reloader=False)

	# Kill program if ctrl+c in terminal
if KeyboardInterrupt:
	logger.close()
	cv2.destroyAllWindows()
	sys.exit()
