import sys, gevent

def spawn(fn, *args, **kwargs):
	main = gevent.getcurrent()
	return gevent.spawn(die_wrapper, main, fn, *args, **kwargs)

def die_wrapper(main, fn, *args, **kwargs):
	try:
		return fn(*args, **kwargs)
	except gevent.GreenletExit:
		raise
	except BaseException, ex:
		main.throw(*sys.exc_info())

