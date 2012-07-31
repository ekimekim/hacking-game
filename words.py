import random

def memoise(fn):
	cache = {}
	def memo_wrapper(*args):
		if args in cache:
			return cache[args]
		else:
			ret = fn(*args)
			cache[args] = ret
			return ret
	return memo_wrapper

@memoise
def dist(word1, word2):
	"""Define a distance function between two words. (amusingly, higher is closer because I wasn't paying attention)
	+2 per letter in the same place
	+1 per shared letter otherwise

	eg. better bummer:
		+6 for b, e, r
		No other shared letters (the first e in better has no match in bummer as its only e is already matched)
	eg. hello goodbye:
		+2 for e, o
	"""
	SAME_PLACE_INC = 2
	SAME_LETTER_INC = 1

	score = 0
	d1, d2 = {}, {}
	for c1, c2 in zip(word1, word2):
		if c1 == c2:
			score += SAME_PLACE_INC - SAME_LETTER_INC # the minus prevents double count
	d1 = letters(word1)
	d2 = letters(word2)
	for c in set(d1.keys() + d2.keys()):
		n1 = d1.get(c, 0)
		n2 = d2.get(c, 0)
		shared = min(n1, n2)
		score += shared * SAME_LETTER_INC
	return score

@memoise
def letters(word):
	d = {}
	for c in word:
		d[c] = d.get(c, 0) + 1
	return d

@memoise
def get_words(path):
	return filter(None, open(path, 'rU').read().split('\n'))

def get_closest(word, path, n):
	"""Get the n closest words to word from words in path, not including itself. Randomises if equal."""
	words = [w for w in get_words(path) if w != word]
	words.sort(key = lambda w: (dist(word, w), random.random()))
	return words[-n:]
