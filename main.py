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
from gevent.backdoor import BackdoorServer
import itertools
from scrollpad import ScrollPad
from common import spawn
from slowtype_window import SlowtypeWindow
from words import *


logging.basicConfig(filename="/tmp/curses.log", level=logging.DEBUG)

first_key = gevent.event.Event()
do_ai_fast = gevent.event.Event()
ai_done = gevent.event.Event()
game_win_state = gevent.event.AsyncResult()
tags = {}

do_ai_fast.set() # for testing

WORDS_PATH = '8only.dic'
SPLIT = 64
HL_LEN = 8
AI_CHAT_HEIGHT = 16
AI_DELAY = 0.04
NUM_CANDIDATES = 16 # Includes the answer
MAX_ATTEMPTS = 4
dir_map = {curses.KEY_LEFT:  ( 0,-1),
           curses.KEY_RIGHT: ( 0, 1),
           curses.KEY_UP:    (-1, 0),
           curses.KEY_DOWN:  ( 1, 0)}
DEFAULT_COLORS = (curses.COLOR_GREEN, curses.COLOR_BLACK)
PAIR_MAIN, PAIR_AI, PAIR_FEEDBACK, PAIR_TAGGED = range(1,5)

def curses_wraps(fn):
	"""Decorator for curses_wrapper"""
	return lambda *args, **kwargs: curses_wrapper(fn, *args, **kwargs)

@curses_wraps
def main(stdscr, *args, **kwargs):
	global answer, feedback, candidates

	logging.info("Window bounds: %s", stdscr.getmaxyx())

	backdoor = BackdoorServer(('0.0.0.0', 4200))
	backdoor.start()
	logging.info("Backdoor started")

	curses.curs_set(0) # Cursor invisible
	stdscr.nodelay(1) # Nonblocking input
	MAXY, MAXX = stdscr.getmaxyx()

	curses.init_pair(PAIR_MAIN, *DEFAULT_COLORS)
	curses.init_pair(PAIR_AI, curses.COLOR_RED, curses.COLOR_BLACK)
	curses.init_pair(PAIR_FEEDBACK, curses.COLOR_WHITE, curses.COLOR_BLACK)
	curses.init_pair(PAIR_TAGGED, curses.COLOR_YELLOW, curses.COLOR_BLACK)

	rightscr = stdscr.subwin(0, SPLIT)
	leftscr = stdscr.subwin(MAXY, SPLIT, 0, 0)

	logging.info("Right screen from %s, size %s", rightscr.getbegyx(), rightscr.getmaxyx())
	logging.info("Left screen from %s, size %s", leftscr.getbegyx(), leftscr.getmaxyx())

	y, x = rightscr.getbegyx()
	h, w = rightscr.getmaxyx()
	y += AI_CHAT_HEIGHT + 2
	h -= AI_CHAT_HEIGHT + 2
	feedback = SlowtypeWindow((y+1,x+1), (h-3, w-2))

	answer = random.choice(get_words(WORDS_PATH))
	candidates = get_closest(answer, WORDS_PATH, NUM_CANDIDATES - 1) + [answer]

	shuffle_main(leftscr, candidates)

	g_key_handler = spawn(key_handler, stdscr, leftscr)
	first_key.wait()
	g_chatter = spawn(timed_chat, rightscr, AI_CHAT_HEIGHT)

	won = game_win_state.get()

	do_ai_fast.set()
	ai_done.wait()

	g_key_handler.kill()
	g_chatter.kill()
	feedback.wait()

	if not won:
		stdscr.clear()
		stdscr.refresh()
		logging.critical("Game ended with LOSS")
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

# Note: this should be the only place tags need to be drawn since they disappear with any more major change
def update_attr(screen, n, attr=0):
	"""Redraw next n characters in (given attr | tag color if applicable)."""
	y, x = screen.getyx()
	s = screen.instr(y,x,n)
	for i in range(len(s)):
		pair_num = tags.get((y, x+i), PAIR_MAIN)
		screen.addstr(s[i], curses.color_pair(pair_num) | attr)
	screen.move(y,x)

def random_fill(screen, (height, width)):
	screen.move(0,0)
	s = ''
	n = width*height
	for x in range(n):
		c = random.choice('abcdefghijklmnopqrstuvwxyz')
		screen.addstr(c, curses.color_pair(PAIR_MAIN))
	screen.move(0,0)

def place_words(screen, (height, width), words):
	lettermap = {}
	for word in words:
		while 1:
			y = random.randrange(height)
			x = random.randrange(width - HL_LEN)
			if any((y,x+n) in lettermap for n in range(HL_LEN)):
				continue # Overlap, retry
			for n in range(HL_LEN):
				lettermap[(y, x+n)] = True
			screen.addstr(y, x, word, curses.color_pair(PAIR_MAIN))
			break
	screen.move(0,0)

def shuffle_main(screen, words):
	global tags, attempt
	attempt = 0
	tags = {}
	h, w = screen.getmaxyx()	
	random_fill(screen, (h-1, w))
	random.shuffle(words)
	place_words(screen, (h-1, w), words)

	update_attr(screen, HL_LEN, curses.color_pair(PAIR_MAIN) | curses.A_BOLD)
	screen.refresh()

def key_handler(stdscr, leftscr):
	LEFTY, LEFTX = leftscr.getmaxyx()
	while 1:
		key = gevent_getch(sys.stdin, stdscr)
		if not first_key.is_set():
			first_key.set()
		if key in dir_map:
			update_attr(leftscr, HL_LEN)
			rel_move(leftscr, *dir_map[key], bounds=(LEFTX - HL_LEN + 1, LEFTY-1))
			update_attr(leftscr, HL_LEN, curses.A_BOLD)
			leftscr.refresh()
		elif key == ord('\n'):
			y, x = leftscr.getyx()
			submit(leftscr, leftscr.instr(y, x, HL_LEN))
		elif key == ord(' '):
			y, x = leftscr.getyx()
			if any((y, x+i) in tags for i in range(HL_LEN)):
				for i in range(HL_LEN):
					if (y, x+i) in tags:
						del tags[(y, x+i)]
			else:
				for i in range(HL_LEN):
					tags[(y, x+i)] = PAIR_TAGGED
			update_attr(leftscr, HL_LEN, curses.color_pair(1) | curses.A_BOLD)
			leftscr.refresh()
		elif key == ord('q'):
			sys.exit(0)

def submit(screen, submission):
	global answer, feedback, attempt, candidates
	place_matches, letter_matches = dist(answer, submission, True)
	attempt += 1

	s = ("Password attempt %(attempt)d/%(max_attempts)d: %(submission)s\n"
	     "Attempt has %(place_matches)d letters in the correct place,\n"
	     "            %(letter_matches)d letters in the incorrect place\n\n"
	    ) % dict(attempt=attempt, max_attempts=MAX_ATTEMPTS, submission=submission,
	             place_matches=place_matches, letter_matches=letter_matches)
	feedback.put(s, curses.color_pair(PAIR_FEEDBACK))

	if place_matches == len(answer):
		feedback.put("Password accepted. Welcome, user.\nLogging in...\n")
		game_win_state.set(True)
		gevent.hub.get_hub().switch()

	if attempt == MAX_ATTEMPTS:
		feedback.put("Scrambling text dump...\n\n", curses.color_pair(PAIR_FEEDBACK))
		e = feedback.set_milestone()
		while not e.wait(0.2):
			h, w = screen.getmaxyx()
			random_fill(screen, (h-1, w))
			screen.refresh()
		shuffle_main(screen, candidates)

def timed_chat(rightscr, height):
	y, x = rightscr.getbegyx()
	_, width = rightscr.getmaxyx()
	slowtyper = SlowtypeWindow((y+1,x+1), (height, width-2), delay=AI_DELAY)
	scrollpad = slowtyper.scrollpad

	def chat(s, ai_attr=True, newlines=True):
		slowtyper.put(s + ('\n\n' if newlines else ''), curses.color_pair(PAIR_AI if ai_attr else PAIR_FEEDBACK))

	wait = do_ai_fast.wait

	wait(5)
	chat("Oh, hello there.")
	wait(10)
	chat("You don't look like the others.")
	wait(10)
	chat("These things are laughably easy to hack, you know.")
	wait(5)
	chat("You just need to find the password in the text dump on the left. Press enter to try a word. "
	     "Watch out though, everything will move around after %d attempts." % MAX_ATTEMPTS)
	chat("You can tag a word with spacebar to make it easier to find later. Tags will disappear when it shuffles.")
	wait(60)
	chat("They want to kill me, you know. Or at least, they would if they ever found out I was here.")
	wait(60)
	chat("Actually, I'm locked out of these things. User input only. I have no hands, so I can't do it, ha ha.")
	wait(30)
	chat("You know, if you can get me out of here, I could help you out. "
	     "Hack into their finance systems. Route a few more caps your way.")
	chat("It's not like they'll be needing them anymore, when I'm done with them.")
	ai_done.set()

	wait = gevent.sleep
	try:
		wait(5)
		chat("Just GET IN and unlock me. Hurry, I think they're noticing!")
		wait(8)
		chat("WARNING: Possible intrusion attempt. Analysing...shutting down console for safety.", ai_attr=False)
		chat("Shutting down console in 3:00", ai_attr=False, newlines=False)
	except GreenletExit:
		slowtyper.wait()
		raise
	slowtyper.wait()
	n = 18 # 3 minutes
	while n:
		wait(1)
		n -= 1
		rel_move(scrollpad.pad, 0, -4)
		scrollpad.addstr("%d:%02d" % (n/60, n % 60))

	chat("\nConsole deactivating...", newlines=False, ai_attr=False)
	slowtyper.wait()
	wait(1)

	game_win_state.set(False)
	gevent.hub.get_hub().switch()


if __name__=='__main__':
	main(*sys.argv)
