import curses
from curses.wrapper import wrapper as curses_wrapper
import time
import sys
import random
import logging

logging.basicConfig(filename="/tmp/curses.log", level=logging.DEBUG)

def curses_wraps(fn):
	"""Decorator for curses_wrapper"""
	return lambda *args, **kwargs: curses_wrapper(fn, *args, **kwargs)


@curses_wraps
def loop(stdscr, initfn, fn, *args, **kwargs):
	global MAXX, MAXY
	curses.curs_set(0) # Cursor invisible
	main_attr = curses.COLOR_GREEN | curses.A_BOLD
	stdscr.nodelay(1) # Nonblocking input
	MAXY, MAXX = stdscr.getmaxyx()

	initfn(stdscr, *args, **kwargs)

	while 1:

		keys = []
		while 1:
			ch = stdscr.getch()
			if ch == -1: break
			keys.append(ch)

		fn(stdscr, keys, *args, **kwargs)
		time.sleep(0.05)


def rel_move(screen, rel_y, rel_x, bounds=None):
	y, x = screen.getyx()
	y += rel_y
	x += rel_x
	if bounds:
		bounds_x, bounds_y = bounds
		logging.debug((x, bounds_x))
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
		screen.addstr(c)
	screen.move(0,0)

SPLIT = 64
HL_LEN = 8
dir_map = {curses.KEY_LEFT:  ( 0,-1),
           curses.KEY_RIGHT: ( 0, 1),
           curses.KEY_UP:    (-1, 0),
           curses.KEY_DOWN:  ( 1, 0)}
DEFAULT_ATTR = curses.COLOR_GREEN
def main(stdscr, keys, *args, **kwargs):
	for key in keys:
		if key in dir_map:
			update_attr(leftscr, HL_LEN, DEFAULT_ATTR)
			rel_move(leftscr, *dir_map[key], bounds=(LEFTX, LEFTY))
			update_attr(leftscr, HL_LEN, DEFAULT_ATTR | curses.A_BOLD)
		elif key == ord('q'):
			sys.exit(0)
	leftscr.refresh()
	rightscr.refresh()

def init(stdscr, *args, **kwargs):
	global leftscr, rightscr, LEFTX, LEFTY, RIGHTX, RIGHTY

	rightscr = stdscr.subwin(0, SPLIT)
	leftscr = stdscr.subwin(MAXY, SPLIT, 0, 0)

	LEFTY, LEFTX = leftscr.getmaxyx()
	RIGHTY, RIGHTX = rightscr.getmaxyx()
	test_fill(leftscr, (LEFTX, LEFTY))


ret = loop(init, main)
sys.exit(ret)
