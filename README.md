# t-rux

t-rux lets you take any audio file and convert it into instructions for playback in an original Teddy Ruxpin bear.

Usage: python t-rux.py inputfile.wav outputfile.wav

Things you should know:

- The higher bitrate file you can supply, the better. If you can, try for 192000bps
- The output file will always be 192000bps
- The output file contains Pulse Position Modulation data, which is how the servo motors in the bear are controlled.
- Eyeball motion is randomly generated. It looks weird if Teddy just stares.
- After running t-rux, you'll still need to create an audio file that combines the two. Place the original audio voice recording in the left channel, and the output file in the right channel.

#todo 
- generate finished wav file from code
- at the very least, make output.wav single channel. Doing that breaks the waveform somehow, so for now I just strip the empty channel and assemble the new audio track in Audition. (inputfile.wav on left ch, ppm channel of outputfile.wav on the right).
