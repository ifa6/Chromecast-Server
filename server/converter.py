#!/usr/bin/env python

import libcommand_center as libcc

#----------------
# Constants
#----------------

HTTP_SERVER_MEDIA_FOLDER = "/mnt/raid/www/media"


## Convert to a Chromecast Friendly format
#
# Checks the video and makes sure the codecs and container are supported.  If 
# not, it converts them and put a copy in the video server folder
#
# @param s - Socket object pointing to the Command Center.  This will be used 
# 	to send updates
# @param infile - The filename of the video file you are converting
# @return - 
def convert(infile):
	# CHeck codecs and packaging
	"avconv -i infile"
	vc = ""
	ac = ""
	cont = ""
	if vc == "x264":
		if ac == "aac":
			if cont == "mp4":
				link(infile)
			else:
				repackage(infile)
		else:
			audio_repackage(infile)
	else:
		video_audio_repackage(infile)
	# When the convertion is complete, tell the command center to remove
	# this item from the queue
	send_update({"complete":infile})

## Link file to Video Server
#
# If not convertion is necesary, this will creates a soft link between the 
# infile and the outfile.
#
# @param s - Socket object pointing to the Command Center (probably not needed)
# @param infile - Input file you are linking to the http server folder.
# @return the return code of th "ln" command
def link(infile):
	# Tell the Command Center that The file is being linked
	send_update("Linking file to http folder")
	#
	outfile = "%s/%s.mp4" % (HTTP_SERVER_MEDIA_FOLDER,infile)
	# Run Command
	ret_code = run_with_progress(["ln","-s","infile",outfile])
	return ret_code

## Repackge file to MP4
#
# If the Audio codec and Video codec are good but the container is bad, this
# will preserve the media streams and repackage as an MP4
#
# @param s - Socket Object pointing to the Command Center
# @param infile - Input file being repackaged as an MP4
# @return return code of the convertion
def repackage(infile):
	send_update("Repackaging file to MP4 (No transcoding)")
	outfile = "%s/%s.mp4" % (HTTP_SERVER_MEDIA_FOLDER,infile)
	ret_code = run_with_progress(["avconv","-i",infile,"-a:c","copy",
			"-v:c","copy",outfile])
	return ret_code

## Transcode Audio to AAC and Repackage to MP4
#
# If the Video codec is good but Audio and Container are bad, this package 
# will preserve the video stream and transcode the audio.
#
# @param s - Socket Object pointing to the command center
# @param infile - Input file being transcoded
# @return return code of the convertion process
def audio_repackage(infile):
	send_update("Transcoding Audio to AAC.")
	outfile = "%s/%s.mp4" % (HTTP_SERVER_MEDIA_FOLDER,infile)
	ret_code = run_with_progress(	["avconv","-i",infile,"-a:c",
		"lib_fdk_aac","-vbr","3","-v:c","copy",outfile])
	return ret_code

## Transcode Audio and Video.  
#
# Transcodes video to H264 and audio to x264 and packages it as an MP4
#
# @param s - Socket Object pointing to the command center
# @param infile - Input file being transcoded
# @return return code of the convertion process
def video_audio_repackage(infile):
	send_update("Transcoding Audio to AAC and Video to H264.")
	outfile = "%s/%s.mp4" % (HTTP_SERVER_MEDIA_FOLDER,infile)
	ret_code = run_with_progress(	["avconv","-i",infile,"-a:c",
		"lib_fdk_aac","-vbr","3","-v:c","libx264","-cbr","23",outfile])
	return ret_code

## Runs a command and gets progress.
#
# Runs the command given in the cmd list.  Every 10 seconds, it parses the 
# STDOUT and figure out how much time is left.
#
# @param s - Socket Object pointing to the command center
# @param cmd - A list of command line program and arguments
# @return return code of the convertion process
def run_with_progress(cmd):
	# Start the process
	p = subprocess.Popen(cmd,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	# Record when the process started
	start_time = time.time()
	# Continue this loop until the process is complete.
	while(p.poll == None):
		# Read the STDERR for 10 seconds
		out = timed_read(p,10)
		# Create a progress object
		req = {"request":"update"}
		# Use RE to parse frames and time
		m = re.match("frame.*?([0-9]*).*time.*?([0-9]*)",out)
		
		# If possible, calcualte percentage (time/totoal time)
		req["time"] = m.group(2)
		req["frame"] = m.group(1)
		req["conversion_time"] = time.time()-start_time
		# Send progress to Command Center, discard the response
		cc_communicate(req)

	# Return the REturn Code
	return p.poll() 


## Timed File Read
#
# Reads the provided file object for a set period of time.  And then returns 
# the last 100 characters.
#
# @param p - POpen object
# @param t - timeout (in seconds)
# @return The last 100 characters of the stream.
def timed_read(p,t):
	# Make the timeout with respect to Unix time
	t += time.time()
	# Output variable
	out = ""
	# Read stdout for t seconds or unitl the process is finished
	while(t > time.time() and p.poll == None):
		out += p.stderr.read(1)

	# Trim output to be less than 100 characters
	if len(out) > 100:
		return out[-99:]
	else:
		return out


## Check the Transcoding Queue
#
# This is a wrapper for the communicate function.  It Asks for a file to 
# transcode.  This file is popped from the transcoding queue
#
# @return the file to convert.  If no file, returns None
def check_queue():
	req = {"request":"queue"}

	resp = cc_communicate(req)

	return resp

def cc_communicate(req):
	req["source"] = "converter"
	resp = libcc.send_recv(req)
	return resp


def loop_forever():
	while(1):
		# Ask if there are any jobs
		job = check_queue()

		# If so, convert them
		if "infile" in job:
			convert(job["infile"])

		# Wait 10 seconds before queueing the queu again
		time.sleep(10)
		

if __name__ == "__main__":
	loop_forever()
