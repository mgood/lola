Lola runs small Python scripts quickly.

The startup time for the Python interpreter is fairly light, but it can become
noticable when running small scripts repeatedly. Lola can reduce this overhead
by starting one interpreter, which you can reuse to repeatedly run scripts.

Example::

  with lola.Runner() as runner:
    for i in xrange(1000):
      runner.call(['myscript.py', str(i)])

The API implements the ``call()``, ``check_call()`` and ``check_output()``
functions from the standard library's ``subprocess`` module.

The name comes from "Lola rennt", aka "Run Lola Run":
http://en.wikipedia.org/wiki/Run_Lola_Run
