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

	def set_milestone(self):
		"""Returns an event, that will be set when the output reaches the current point in the queue."""
		e = Event()
		self.queue.put(e)
		return e

	def wait(self):
		self.set_milestone().wait()
