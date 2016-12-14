import pyaudio, wave, time, numpy as np

CHUNK = 256
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
THRESHOLD = 1.5e7

audio = pyaudio.PyAudio()

wf = wave.open("claps/bathroom1.wav", 'rb')
wf2 = wave.open("claps/bathroom1.wav", 'rb')

clap_data = ''
while True:
    data = wf.readframes(1024)
    clap_data += data
    if len(data) < 1024: break

class Clapback(object):
    def __init__(self):
        self.position = 0
        self.queue = clap_data*2

    def chunk_for(time):
        pass

    def callback(self, in_data, frame_count, time_info, status):
        end_pos = frame_count*4 + self.position
        data = self.queue[self.position:end_pos]
        self.position = end_pos
        print frame_count, len(data)
        return (data, pyaudio.paContinue)

cb = Clapback()

print wf.getframerate()
stream = audio.open(format=audio.get_format_from_width(wf.getsampwidth()),
                channels=wf.getnchannels(),
                rate=wf.getframerate(),
                output=True,
                stream_callback=cb.callback)

stream.start_stream()

# wait for stream to finish (5)
while stream.is_active():
    time.sleep(0.1)

# stop stream (6)
stream.stop_stream()
stream.close()
wf.close()

audio.terminate()
