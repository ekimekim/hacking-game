import curses
from curses.wrapper import wrapper as curses_wrapper

def curses_wraps(fn):
	"""Decorator for curses_wrapper"""
	return lambda *args, **kwargs: curses_wrapper(fn, *args, **kwargs)

def init():
	# Doesn't need running if curses_wrapper is used.
	screen = curses.initscr()
	curses.noecho()
	curses.cbreak()
	screen.keypad(1) # Enable escape interpretation for special keys
	return screen


@curses_wraps
def main(stdscr, *args, **kwargs):
#	curses.curs_set(0) # Cursor invisible
#	main_attr = curses.COLOR_GREEN | curses.A_BOLD
#	stdscr.nodelay(1) # Nonblocking input
	MAXY, MAXX = stdscr.getmaxyx()
	
	rightwin = stdscr.subwin(0, 20)
	leftwin = stdscr.subwin(MAXY, 20, 0, 0)

	leftwin.border()
	rightwin.border(0)
	leftwin.addstr("left")
	stdscr.addstr("right")

#	leftwin.refresh()
#	rightwin.refresh()
	stdscr.refresh()
	ret = stdscr.getch()
	return ret

ret = main()
print ret
