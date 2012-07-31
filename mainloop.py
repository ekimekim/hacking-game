import curses
from curses.wrapper import wrapper as curses_wrapper
import time
import sys
import random
import logging
from gevent.select import select
import gevent.queue
import gevent
import gevent.hub
import gevent.event
import itertools
from scrollpad import ScrollPad
from common import spawn
from slowtype_window import SlowtypeWindow

logging.basicConfig(filename="/tmp/curses.log", level=logging.DEBUG)

do_ai_fast = gevent.event.Event()
ai_done = gevent.event.Event()

SPLIT = 64
HL_LEN = 8
AI_CHAT_HEIGHT = 16
dir_map = {curses.KEY_LEFT:  ( 0,-1),
           curses.KEY_RIGHT: ( 0, 1),
           curses.KEY_UP:    (-1, 0),
           curses.KEY_DOWN:  ( 1, 0)}
DEFAULT_COLORS = (curses.COLOR_GREEN, curses.COLOR_BLACK)
PAIR_MAIN, PAIR_AI, PAIR_FEEDBACK = range(1,4)

def curses_wraps(fn):
	"""Decorator for curses_wrapper"""
	return lambda *args, **kwargs: curses_wrapper(fn, *args, **kwargs)

@curses_wraps
def main(stdscr, *args, **kwargs):
	logging.info("Window bounds: %s", stdscr.getmaxyx())

	curses.curs_set(0) # Cursor invisible
	stdscr.nodelay(1) # Nonblocking input
	MAXY, MAXX = stdscr.getmaxyx()

	curses.init_pair(PAIR_MAIN, *DEFAULT_COLORS)
	curses.init_pair(PAIR_AI, curses.COLOR_RED, curses.COLOR_BLACK)
	curses.init_pair(PAIR_FEEDBACK, curses.COLOR_WHITE, curses.COLOR_BLACK)

	rightscr = stdscr.subwin(0, SPLIT)
	leftscr = stdscr.subwin(MAXY, SPLIT, 0, 0)

	logging.info("Right screen from %s, size %s", rightscr.getbegyx(), rightscr.getmaxyx())
	logging.info("Left screen from %s, size %s", leftscr.getbegyx(), leftscr.getmaxyx())

	test_fill(leftscr, leftscr.getmaxyx())
	nice_fill(leftscr, leftscr.getmaxyx(), ("%.6f" % random.random() for x in itertools.count()))
	update_attr(leftscr, HL_LEN, curses.color_pair(1) | curses.A_BOLD)
	leftscr.refresh()

	spawn(key_handler, stdscr, leftscr)
	spawn(timed_chat, rightscr, AI_CHAT_HEIGHT)

	gevent.hub.get_hub().switch()


def gevent_getch(fd, scr):
	r = []
	while fd not in r:
		r, w, x = select([fd], [], [])
	return scr.getch()

def rel_move(screen, rel_y, rel_x, bounds=None):
	y, x = screen.getyx()
	y += rel_y
	x += rel_x
	if bounds:
		bounds_x, bounds_y = bounds
		x = max(0, min(x, bounds_x-1))
		y = max(0, min(y, bounds_y-1))
	screen.move(y,x)

def update_attr(screen, n, attr):
	"""Redraw next n characters in attr."""
	y, x = screen.getyx()
	s = screen.instr(y,x,n)
	screen.addstr(s,attr)
	screen.move(y,x)

def test_fill(screen, (width,height)):
	screen.move(0,0)
	s = ''
	n = width*height-1
	for x in range(n):
		c = random.choice('abcdefghijklmnopqrstuvwxyz')
		screen.addstr(c, curses.color_pair(1))
	screen.move(0,0)

def nice_fill(screen, (height, width), data):
	cols = 3
	col_space = 4
	data = iter(data)
	for y in range(1, height, 2):
		logging.debug("y=%s", y)
		screen.move(y, 0)
		for col in range(cols):
			rel_move(screen, 0, col_space)
			screen.addstr(data.next(), curses.color_pair(1))
	screen.move(0,0)

def key_handler(stdscr, leftscr):
	LEFTY, LEFTX = leftscr.getmaxyx()
	while 1:
		key = gevent_getch(sys.stdin, stdscr)
		if key in dir_map:
			update_attr(leftscr, HL_LEN, curses.color_pair(1))
			rel_move(leftscr, *dir_map[key], bounds=(LEFTX - HL_LEN + 1, LEFTY))
			update_attr(leftscr, HL_LEN, curses.color_pair(1) | curses.A_BOLD)
			leftscr.refresh()
		elif key == ord('q'):
			sys.exit(0)

def timed_chat(rightscr, height):
	y, x = rightscr.getbegyx()
	_, width = rightscr.getmaxyx()
	slowtyper = SlowtypeWindow((y+1,x+1), (height, width-2))
	scrollpad = slowtyper.scrollpad

	def chat(s, ai_attr=True, newlines=True):
		slowtyper.put(s + ('\n\n' if newlines else ''), curses.color_pair(PAIR_AI if ai_attr else PAIR_FEEDBACK))

	wait = do_ai_fast.wait

	wait(5)
	chat("Oh, hello there.")
	wait(5)
	chat("You don't look like the others.")
	wait(5)
	chat("These things are laughably easy to hack, you know.")
	wait(2)
	chat("You just need to find the correct sequence from the text dump on the left.")
	wait(20)
	chat("They want to kill me, you know. Or at least, they would if they ever found out I was here.")
	wait(60)
	chat("Actually, I'm locked out of these things. User input only. I have no hands, so I can't do it, ha ha.")
	wait(10)
	chat("You know, if you can get me out of here, I could help you out. "
	     "Hack into their finance systems. Route a few more caps your way.")
	ai_done.set()
	gevent.sleep()
	wait(5)
	chat("Just GET IN and unlock me. Hurry, I think they're noticing!")
	wait(8)
	chat("WARNING: Possible intrusion attempt. Analysing...shutting down console for safety.", ai_attr=False)
	chat("Shutting down console in 3:00", ai_attr=False, newlines=False)
	slowtyper.wait()
	n = 180 # 3 minutes
	while n:
		ai_stop.wait(1)
		n -= 1
		rel_move(scrollpad.pad, 0, -4)
		scrollpad.addstr("%d:%02d" % (n/60, n % 60))
	# TODO lose


if __name__=='__main__':
	main(*sys.argv)
