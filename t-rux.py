'''
USAGE:
python3 t-rux.py inputfile.wav outputfile.wav

You must use 16-bit audio files. If possible, record at 192,000 bit/sample rate. 

You will need to load both into the audio editor of your choice when done. Voice
data goes in the left channel, while PPM data goes in the right. Then find a 
tape recorder and hook it up/record. 

If you don't use a tape recorder and try to play the sound directly into
the bear (e.g. maybe you use one of those CD to Tape adapters), you will need 
to invert the PPM signal. See the comments in GenSignal.generate for more info

# short term todo 
# 
# - post to github when complete
#
# - build output file with input waveform, too. shouldn't be too hard, but there
#   appears to be some syncing necessary when I combine the files manually. So 
#	maybe it's not possible. 
# 
# - at the very least, make output.wav single channel. Doing that breaks the
#   waveform somehow, so for now I just strip the empty channel and assemble the 
#   new audio track in Audition. (inputfile.wav on left ch, ppm channel of 
#   outputfile.wav on the right).
'''


# Amplitude code derived from:
# http://myinspirationinformation.com/uncategorized/audio-signals-in-python/

#required libraries
import scipy.io.wavfile
import numpy as np
import math
from random import randint
import pyperclip # Just needed for debugging
import sys

# Constants
GROUP_SIZE = 9
PPM_FRAME_WIDTH = .0225

temp_list = []
normal_list = []
sample_list = []
ppm_frames = []
channel_width_list = []
eye_position_list = []
eye_open_counter = 1
eye_closed_counter = 0
eye_open_duration = randint(45,400) # 400 is too long for short wavs

channel1 = 700 # Not used (Channel 0 sometimes. Tried to be consistent at 1)
channel2 = 700 ### Eyes
channel3 = 700 ### Upper Lip
channel4 = 700 ### Bottom Lip
channel5 = 700 # Route audio to Grubby or Teddy (not used here)
channel6 = 700 # Grubby Eyes (not used here)
channel7 = 700 # Grubby Upper Lip (not used here)
channel8 = 700 # Grubby Bottom Lip (not used here)

###########
## Check for proper number of args
###########

if len(sys.argv) != 3:
	raise ValueError("Proper syntax is 'python3 t-rux.py inputfile.wav outputfile.wav'" )
else:
	input_file = sys.argv[1]
	output_file = sys.argv[2]

###########
## This gets the ball rolling
###########

# read the wav file. File must be mono, 16-bit. Highest sample rate 
# you can make (tested up to 192000)
rate,audData=scipy.io.wavfile.read(input_file)

# check to make sure audio rate of input file is acceptable
if rate < 192000:
	print("It's highly recommended to use an input file recorded at 192kbps.")

#determine length of wav file
wav_duration = audData.shape[0] / rate

# create a time array in .0225 increments. We'll take a sample
# at each time
time = np.arange(0, wav_duration, PPM_FRAME_WIDTH)

# determines number of wav samples to skip between amplitude measurements
# sample_step needs to be int, so that's what // does. That was new to me.
sample_step = audData.shape[0] // len(time) 
#print(sample_step)

# defines the sample in audData to start at. Will incremement in loop
# using sample_step from above.
next_sample = 0

###########
## Now we have to actually determine amplitude at each sample
##
## Each sample will be a number between 0 and 32760 - the max amplitude of a
## 16-bit wav file.
###########


#for i in range (1,(len(time))):
for i in time:
	# gets amplitude data
	blockRMS = np.sqrt(audData[next_sample]**2) 
	#print(blockRMS)
	
	# increments next_sample
	next_sample += sample_step

	# and adds this sample to the list of samples
	sample_list.append(blockRMS)

# Rebuilding sample_list to reduce the amount of variability over time. This works
# by grouping GROUP_SIZE number of samples together from sample_list and setting 
# them all to the max value in the group.

# Example if the GROUP_SIZE is set to 5 (above in constants):

# sample_list might look like: [1, 6, 8, 7, 2, 150, 101, 5, 250, 19, ..., 50, 49, 48, 65, 37] 
# 		                        |-----*-----|  |------------***---|	      |-----------**---|

# after this, it will look like: [8, 8, 8, 8, 8, 250, 250, 250, 250, 250, ..., 65, 65, 65, 65, 65]
# 					              |-----------|  |---------------------|       |----------------|

x = 0

while x < len(sample_list): 
    sample_list[x:x+GROUP_SIZE] = [max(sample_list[x:x+GROUP_SIZE])] * GROUP_SIZE
    x += GROUP_SIZE



## Now we calculate the step. There's an 800us range, so we divide the min-max
# difference by 800 (I think it might be 1000us range, but I'm using
# 800 to not limit it out). Also, it doesn't matter anymore since we're
# reducing the number to one in a 0.0 - 100.0 range later.

step = (max(sample_list)-min(sample_list)) / 800



## Finally, we divide each amplitude (now called channel_width) in the list 
## by the step and add 700 (700us is the channel width for the zero position 
## on the motor - 1100us is middle, 1500us is max position)
##
## This gets us the channel width that we'll use for both channels 3 and 4.
## Channel 3 will be run through a randmomizer/reducer to make it less active
## and more variable

for sample in sample_list:

	# normalizes = makes min amplitude 0
	channel_width = sample - min(sample_list) 
	
	# calculates the difference between mix/max amplitude and adds 700
	# 700us is our 0 (or "off")
	channel_width = (channel_width / step) + 700
	
	# Adds this to the channel_width_list that keeps track of all amplitudes
	# for each channel at each sample time
	channel_width_list.append(round(channel_width))



# Eyeball randomness

# Want blinks to go the full range. No half blinks. Let's say a blink lasts 1s, 
# so that's ~45 pulses. So, all we need to do is generate 45 1400's, followed by
# randint(45,300) 700's for the duration of this. (300 is max num of samples 
# before next blink. ~6.75s)

for i in sample_list:

	if eye_open_counter >=1:
		eye_open_counter += 1
		eye_position_list.append(700) # open

	if eye_closed_counter >=1:
		eye_closed_counter += 1
		eye_position_list.append(1400) # closed

	if eye_closed_counter == 45:
		eye_open_counter = 1
		eye_closed_counter = 0
		eye_open_duration = randint(45,300) # blink every 1 to 6.75s

	if eye_open_counter == eye_open_duration:
		eye_open_counter = 0
		eye_closed_counter = 1



# Upper Lip Wobble

# Just for Channel 3, want to introduce some random wobble. Just using a 
# random divisor with the calculated channel width. Max channel width is 
# 1500 (some say 1700, but I don't want to max it out), min is 700, so divide 
# by a random number between 1 and 2.14 (~1500/700).

# This only reduces the range of the upper lip. Probably ok, but may look odd.
# Can change to divide by 0-2 if needed (with if/then for upper limit, too)

def upper_wobble(x):
	divisor = randint(100,214)/100 #no need to mess with floats
	upper_channel_width = round(x / divisor)
	
	if upper_channel_width < 700:
		upper_channel_width = 700 # set to "0" so upper lip doesn't move when not talking

	return upper_channel_width



# Ok, let's put it all together. I don't care about time since I'm 100% going to
# put these in at .0225 second intervals, so this really just needs to be 
# [ch2, ch3, ch4] (Channel 1 is never used)

for width in range(len(channel_width_list)):

	channel2 = eye_position_list[width]
	channel3 = upper_wobble(int(channel_width_list[width]))
	channel4 = channel_width_list[width] # lower jaw

	# converting to 0.0 - 100.0 float since that's what the PPM code wants
	# can simplify this later, but meh. Easy enough to convert here.
	ppm_frames.append({1: ((channel1-700)/8), 2: ((channel2-700)/8), 3: ((channel3-700)/8), 4: ((channel4-700)/8), 5: 
		((channel5-700)/8), 6: ((channel6-700)/8), 7: ((channel7-700)/8), 8: ((channel8-700)/8)}) 



### Now this is fed to the PPM waveform generator:



# Original project: https://github.com/kangsterizer/Audio_PPM_Linux

#!/usr/bin/python
# Licensed under the terms of the GPLv3
# Copyright 2010 kang@insecure.ws
# See http://www.gnu.org/licenses/gpl-3.0.txt or the LICENSE file

import wave 
from struct import pack
import os
import signal

# Need to init this dict
channels = {1: 0.0, # not used
	2: 50.0, # eyes set to center
	3: 50.0, # upper jaw set to center
	4: 50.0, # lower jaw set to center
	5: 0.0,  # not used
	6: 0.0,  # not used
	7: 0.0,  # not used
	8: 0.0,  # not used
}

class GenSignal:
	
	signal = ""
	mmdiv = float(rate)/10000
	samples = int(PPM_FRAME_WIDTH*rate) #992.25 # What is this 992.25???
	amplitude = 20262 #max for 16-bit file is 32760

	def generate(self): 
		clist = []
		#start with a stop
		
		'''
		# When this goes to tape, the signal is flipped (inverse). So this code
		# gives a proper signal, but since we have to compensate for the inverse
		# we have to flip the polarity.

		# Proper
		clist += [-self.amplitude]*int(self.mmdiv*4)
	
		for i in channels:
			clist += [self.amplitude]*int(self.mmdiv*7)
			servo = channels[i]*0.75/100
			signal = (self.mmdiv*10)*servo
			clist += [self.amplitude]*int( signal )
			clist += [-self.amplitude]*int(self.mmdiv*4)
		'''

		# Inverse
		clist += [self.amplitude]*int(self.mmdiv*4)
	
		for i in channels:
			clist += [-self.amplitude]*int(self.mmdiv*7)
			servo = channels[i]*0.75/100
			signal = (self.mmdiv*10)*servo
			clist += [-self.amplitude]*int( signal )
			clist += [self.amplitude]*int(self.mmdiv*4)


		#complete the ppm signal with a starting null signal that fills in the
		#22.5ms frame (here f.ex 992 self.samples)
		# ^^^^^Original comment - not sure what "f.ex 992 self.samples" means
		mylist = []
		for i in range(0, self.samples-len(clist)):
			mylist += [0]

		#add our ppm channels
		mylist += clist
		self.signal = pack('<'+self.samples*'l',*mylist)
		
class PPM:
	signal_bytearray = bytearray()
	def __init__(self):
		for dic in ppm_frames:
			for key in dic:
				channels[key] = dic[key]
				# deadening motor noise for small, useless movements
				if channels[key] <= 1.5:
					channels[key] = 0
				
			gen.generate()
			self.signal_bytearray += gen.signal

		self.newwave()

	def newwave(self):
		self.file = wave.open(output_file, mode='wb')
		self.file.setparams((2, 2, 192000, 192000*4, 'NONE', 'noncompressed'))
		self.file.writeframes(PPM.signal_bytearray)
		self.file.close()
		print("Finished")

gen = GenSignal()

app = PPM()







