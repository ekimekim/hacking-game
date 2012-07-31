from scrollpad import ScrollPad
from gevent.queue import Queue
from gevent.event import Event
from gevent import sleep
from common import spawn

class SlowtypeWindow(object):
	def __init__(self, pos, size, delay=0.1):
		self.scrollpad = ScrollPad(pos, size)
		self.queue = Queue()
		self.g_writer = spawn(self.writer)
		self.delay = delay

	def writer(self):
		for x in self.queue:
			if type(x) == Event:
				x.set()
				continue
			s, attr = x
			for c in s:
				self.scrollpad.addstr(c, attr)
				sleep(self.delay)

	def put(self, s, attr=None):
		self.queue.put((s, attr))

	def wait(self):
		e = Event()
		self.queue.put(e) # Add a milestone so we can be informed of when it reaches that point of queue
		e.wait()
