import os
import subprocess
import sys
import traceback
import _multiprocessing
from multiprocessing.connection import Listener, Client


class Runner(object):
  """Run a Python interpreter in the background for executing scripts.

  It implements a subprocess-like API, providing equivalent functions to
  ``call()``, ``check_call()``, and ``check_output()``.

  Example::

    with lola.Runner() as runner:
      retcode = runner.call(['myscript.py', 'arg1', 'arg2'])
      runner.check_call(['myscript.py', 'arg3', 'arg4'])
      out = runner.check_output(['myscript.py', 'arg3', 'arg4'])

      # redirect stdout, stderr, and provide a custom environment dict
      runner.call(['myscript.py', 'arg1', 'arg2'],
                  stdout=open('out.txt', 'w'),
                  stderr=subprocess.STDOUT,
                  env=env)

    """
  def __init__(self, python=None):
    if python is None:
      python = sys.executable

    self._listener = listener = Listener()
    subprocess.Popen([python, __file__, listener.address])
    self._cnx = listener.accept()

  def close(self):
    self._expect_connected()
    try:
      self._cnx.close()
    finally:
      try:
        self._listener.close()
      finally:
        self._cnx = self._listener = None

  def __enter__(self):
    return self

  def __exit__(self, *args):
    self.close()

  def call(self, *popenargs, **kwargs):
    """Run Python script with arguments.  Wait for command to complete, then
    return the return code.

    The arguments are the same as for the subprocess.Popen constructor.
    """
    retcode, _, _ = self._call(*popenargs, **kwargs)
    return retcode

  def check_call(self, *popenargs, **kwargs):
    """Run Python script with arguments.  Wait for command to complete.  If
    the exit code was zero then return, otherwise raise
    subprocess.CalledProcessError.  The CalledProcessError object will have the
    return code in the returncode attribute.

    The arguments are the same as for the Popen constructor.
    """
    retcode = self.call(*popenargs, **kwargs)
    if retcode:
      cmd = kwargs.get("args")
      if cmd is None:
        cmd = popenargs[0]
      raise subprocess.CalledProcessError(retcode, cmd)
    return retcode

  def check_output(self, *popenargs, **kwargs):
    """Run command with arguments and return its output as a byte string.

    If the exit code was non-zero it raises a CalledProcessError.  The
    CalledProcessError object will have the return code in the returncode
    attribute and output in the output attribute.

    The arguments are the same as for the Popen constructor.

    The stdout argument is not allowed as it is used internally.
    To capture standard error in the result, use stderr=STDOUT.
    """
    retcode, stdout, _ = self._call(stdout=subprocess.PIPE,
                                    *popenargs, **kwargs)
    if retcode:
      cmd = kwargs.get("args")
      if cmd is None:
        cmd = popenargs[0]
      err = subprocess.CalledProcessError(retcode, cmd)
      err.output = stdout
      raise err
    return stdout

  def _call(self, args, bufsize=0, executable=None,
            stdin=None, stdout=None, stderr=None,
            preexec_fn=None, close_fds=False, shell=False,
            cwd=None, env=None, universal_newlines=False,
            startupinfo=None, creationflags=0):
    self._expect_connected()

    fds = []
    def mkfd(fp):
      if fp in (None, subprocess.STDOUT, subprocess.PIPE):
        return fp
      elif isinstance(fp, int):
        fds.append(fp)
      else:
        fds.append(fp.fileno())
      return len(fds) - 1

    stdin = mkfd(stdin)
    stdout = mkfd(stdout)
    stderr = mkfd(stderr)

    self._cnx.send(((args, bufsize, executable, stdin, stdout, stderr,
                     preexec_fn, close_fds, shell, cwd, env, universal_newlines,
                     startupinfo, creationflags),
                    len(fds)))
    for fd in fds:
      _multiprocessing.sendfd(self._cnx.fileno(), fd)
    return self._cnx.recv()

  def _expect_connected(self):
    if self._cnx is None:
      raise ValueError('Runner is closed')


def listen(address):
  cnx = Client(address)
  while True:
    try:
      args, num_fds = cnx.recv()
    except EOFError:
      break
    fds = dict(
      (idx, _multiprocessing.recvfd(cnx.fileno()))
      for idx in range(num_fds)
    )
    proc = _PyPopen(*args, _fd_map=fds)
    stdout, stderr = proc.communicate()
    retcode = proc.poll()
    cnx.send((retcode, stdout, stderr))


class _PyPopen(subprocess.Popen):
  def __init__(self, args, bufsize=0, executable=None,
               stdin=None, stdout=None, stderr=None,
               preexec_fn=None, close_fds=False, shell=False,
               cwd=None, env=None, universal_newlines=False,
               startupinfo=None, creationflags=0, _fd_map=None):
    """
      Run a Python script in a forked interpreter.

      This class uses the same interface as Popen, and can be used as a
      replacement to run Python scripts in a forked process, without executing
      a new Python interpreter.
    """
    if shell:
      raise ValueError()

    if _fd_map is not None:
      stdin = _fd_map.get(stdin, stdin)
      stdout = _fd_map.get(stdout, stdout)
      stderr = _fd_map.get(stderr, stderr)

    def exec_python(args=args, executable=executable):
      if isinstance(args, basestring):
        args = [args]
      else:
        args = list(args)

      if executable is None:
        executable = args[0]

      if preexec_fn:
        preexec_fn()

      sys.argv = args

      if env is not None:
        for key in list(os.environ):
          if key not in env:
            del os.environ[key]
        os.environ.update(env)

      try:
        p_globals = dict((k,getattr(__builtins__, k))
                         for k in dir(__builtins__))
        p_globals['__name__'] = '__main__'
        p_globals['__file__'] = os.path.abspath(executable)
        execfile(executable, p_globals)
      except SystemExit as e:
        sys.stdout.flush()
        if isinstance(e.code, int):
          os._exit(e.code)
        elif e.code is None:
          os._exit(0)
        else:
          print >>sys.stderr, e.code
          os._exit(1)
      except:
        sys.stdout.flush()
        traceback.print_exc()
        os._exit(255)
      else:
        sys.stdout.flush()
        os._exit(0)

    subprocess.Popen.__init__(self, args, bufsize, executable, stdin, stdout,
                              stderr, exec_python, close_fds, shell, cwd, env,
                              universal_newlines, startupinfo, creationflags)


if __name__ == '__main__':
  address = sys.argv[1]
  listen(address)
