from scrollpad import ScrollPad
from gevent.queue import Queue
from gevent.event import Event
from gevent import sleep
from common import spawn

class SlowtypeWindow(object):
	def __init__(self, pos, size, delay=0.01):
		self.scrollpad = ScrollPad(pos, size)
		self.queue = Queue()
		self.g_writer = spawn(self.writer)
		self.delay = delay
		_, self.width = size

	def writer(self):
		line_pos = 0
		for x in self.queue:
			if type(x) == Event:
				x.set()
				continue
			s, attr = x
			lines = s.split('\n')
			for l in range(len(lines)):
				line = lines[l]
				words = line.split(' ')
				for w in range(len(words)):
					word = words[w]
					line_pos += len(word)
					if line_pos > self.width:
						self.scrollpad.addstr('\n', attr)
						line_pos = len(word)
					for c in word:
						self.scrollpad.addstr(c, attr)
						sleep(self.delay)
					if w != len(words) - 1:
						if line_pos in (self.width, self.width-1):
							if line_pos == self.width-1:
								self.scrollpad.addstr('\n', attr)
							line_pos = 0
						else:
							self.scrollpad.addstr(' ', attr)
							line_pos += 1
				if l != len(lines) - 1:
					self.scrollpad.addstr('\n', attr)
					line_pos = 0

	def put(self, s, attr=None):
		self.queue.put((s, attr))

	def set_milestone(self):
		"""Returns an event, that will be set when the output reaches the current point in the queue."""
		e = Event()
		self.queue.put(e)
		return e

	def wait(self):
		self.set_milestone().wait()
