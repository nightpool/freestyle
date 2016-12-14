
import pyaudio, numpy as np
import subprocess, time
from collections import namedtuple

CHUNK = 256
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
THRESHOLD = 1.5e7

Chunk = namedtuple('Chunk', 'data time')
Clap = namedtuple('Clap', 'time duration magnitude',)

audio = pyaudio.PyAudio()

class MicrophoneFeed(object):
    def __init__(self):
        self.enabled = True
        self.stream = audio.open(format=FORMAT, channels=CHANNELS, rate=RATE,
                                  input=True, frames_per_buffer=CHUNK)
        self.t = 0.0

    def __iter__(self):
        while self.enabled:
            data = self.stream.read(CHUNK)
            chunk = np.fromstring(data, 'int16')
            t = self.t
            self.t += float(CHUNK) / RATE
            yield Chunk(chunk, t)

    def close(self):
        self.stream.stop_stream()
        self.enabled = False

    def open(self):
        self.stream.start_stream()
        self.enabled = True

class VerboseFeed(object):
    def __init__(self, feed):
        self.feed = feed

    def __iter__(self):
        for c in self.feed:
            # print('*' * (abs(c.data).sum() // 250000))
            yield c

SLOW = 0.050
FAST = 0.45

class EdgeDetector():
    "Call a sufficiently noisy event a clap."

    def __init__(self, feed, threshold):
        self.slow = 0
        self.fast = 0
        self.threshold = threshold
        self.feed = feed

        self.current_clap = None
        self.current_mag = 0

        self.start = None
        self.beat = 0.25
        self.current_beat = 0
        self.last_clap = 0

        self.has_init = 0

    def __iter__(self):
        for c in self.feed:
            edge = self.step(c)

            if not self.has_init:
                if edge > self.threshold:
                    continue
                else:
                    self.has_init = True

            if self.start:
                beat = (c.time - self.start) // self.beat
                if beat > self.current_beat:
                    self.current_beat = beat
                    print 'beat {}/{}'.format(self.current_beat, self.last_clap)

            if edge > self.threshold:
                if self.current_clap:
                    self.current_mag = max(edge, self.current_mag)
                else:
                    self.current_clap = c.time
                    self.current_mag = edge
            elif self.current_clap:
                duration = c.time - self.current_clap
                clap = Clap(self.current_clap, duration, self.current_mag)
                if not self.start:
                    self.start = self.current_clap
                self.last_clap = (c.time - self.start) // self.beat
                print "lc", self.last_clap
                self.current_clap = None
                self.current_mag = 0
                self.empty = 0
                yield ('clap', clap)
            elif self.current_beat - self.last_clap > 2:
                self.start = None
                self.current_beat = 0
                self.last_clap = 0
                yield ('break', self.current_beat)

    def step(self, chunk):
        val = abs(chunk.data).sum()
        self.slow = val * SLOW + self.slow * (1-SLOW)
        self.fast = val * FAST + self.fast * (1-FAST)
        edge = self.fast - self.slow
        s = ('*' * (edge // 200000))
        if s: print s
        return edge

def play(name, delay):
    time.sleep(delay)
    subprocess.Popen(['afplay', 'claps/{}.wav'.format(name)])

def tempo():
    mic = MicrophoneFeed()
    detector = EdgeDetector(VerboseFeed(mic), 500000)

    tempo = []
    beat = 0

    for t, clap in detector:
        if t == 'clap':
            print 'clap'
            tempo.append(clap)
        if len(tempo) >= 4:
            break
    mic.close()
    print "playing...."
    for i, c in enumerate(tempo[:]):
        diff = (c.time - tempo[i-1].time if i > 0
                    else tempo[-1].time - tempo[-2].time)
        if i > 0: beat += diff/3.
        play("bathroom1", diff)
    tempo = []

    print "beat is {}".format(beat)
    detector.beat = beat
    time.sleep(1)
    print "listening...."
    mic.open()
    claps = []
    while True:
        detector.start = None
        detector.current_beat = 0
        for thing, clap in detector:
            print('=== CLAP === ', clap)
            if thing == 'clap':
                claps.append(clap)
            if thing == 'break' and claps:
                break
        mic.close()

        print '--------'
        for c in claps:
            print "Clap("
            print " t: {:4}".format(c.time)
            print " d: {:4}".format(c.duration)
            print " m: {:4}".format(c.magnitude)
            print
        for i, c in enumerate(claps):
            diff = c.time - claps[i-1].time if i > 0 else 0
            play("bathroom1", diff)
        claps = []
        detector.start = None
        detector.current_beat = 0
        time.sleep(1)
        print "okay, let's try something else"
        mic.open()


if __name__ == '__main__':
    tempo()
