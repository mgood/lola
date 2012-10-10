import contextlib
import os
import shutil
import tempfile
import subprocess

import lola
from expecter import expect

DEVNULL = open('/dev/null', 'w')


@contextlib.contextmanager
def temp_directory():
  tmpdir = tempfile.mkdtemp()
  try:
    yield tmpdir
  finally:
    shutil.rmtree(tmpdir)


def test_success_retcode():
  with lola.Runner() as runner:
    retcode = runner.call(['test_scripts/success.py'],
                          stdout=DEVNULL, stderr=DEVNULL)
  expect(retcode) == 0


def test_failure_retcode():
  with lola.Runner() as runner:
    retcode = runner.call(['test_scripts/fail.py'],
                          stdout=DEVNULL, stderr=DEVNULL)
  expect(retcode) == 1


def test_exception():
  with lola.Runner() as runner:
    retcode = runner.call(['test_scripts/exception.py'],
                          stdout=DEVNULL, stderr=DEVNULL)
  expect(retcode) == 255


def test_check_call_success():
  with lola.Runner() as runner:
    retcode = runner.check_call(['test_scripts/success.py'],
                                stdout=DEVNULL, stderr=DEVNULL)
  expect(retcode) == 0


def test_check_call_error():
  try:
    with lola.Runner() as runner:
      runner.check_call(['test_scripts/fail.py'],
                        stdout=DEVNULL, stderr=DEVNULL)
  except subprocess.CalledProcessError as e:
    expect(e.returncode) == 1
  else:
    assert False, 'Should have raise a CalledProcessError'


def test_output_to_file():
  with temp_directory() as tmpdir:
    outfile = os.path.join(tmpdir, 'out.txt')
    errfile = os.path.join(tmpdir, 'err.txt')

    with lola.Runner() as runner:
      runner.check_call(['test_scripts/output.py'],
                        stdout=open(outfile, 'w'), stderr=open(errfile, 'w'))

    expect(open(outfile).read()) == 'outputting\n'
    expect(open(errfile).read()) == 'erroring\n'


def test_stderr_to_stdout():
  with temp_directory() as tmpdir:
    outfile = os.path.join(tmpdir, 'out.txt')

    with lola.Runner() as runner:
      runner.check_call(['test_scripts/output.py'],
                        stdout=open(outfile, 'w'), stderr=subprocess.STDOUT)

    expect(open(outfile).read()) == 'outputting\nerroring\n'


def test_check_output():
  with lola.Runner() as runner:
    out = runner.check_output(['test_scripts/output.py'],
                              stderr=subprocess.STDOUT)
  expect(out) == 'outputting\nerroring\n'


def test_check_output_error():
  try:
    with lola.Runner() as runner:
      runner.check_output(['test_scripts/fail.py'], stderr=subprocess.STDOUT)
  except subprocess.CalledProcessError as e:
    expect(e.returncode) == 1
    expect(e.output) == 'failing'
  else:
    assert False, 'Should have raise a CalledProcessError'


def test_cwd():
  with temp_directory() as tmpdir:
    with lola.Runner() as runner:
      out = runner.check_output([os.path.abspath('test_scripts/pwd.py')],
                                cwd=tmpdir)
    # use samefile instead of string comparison since on OSX we get "/var" as
    # tmpdir, but "/private/var" from the pwd script
    assert os.path.samefile(out, tmpdir)


def test_env():
  env = os.environ.copy()
  env['LOLA_ENV_TEST'] = 'test value'

  with lola.Runner() as runner:
    out = runner.check_output(['test_scripts/env.py', 'LOLA_ENV_TEST'], env=env)

  expect(out) == 'test value'


def test_env_overrides_parent():
  env = os.environ.copy()
  # this key set in the parent process should not be inherited when
  # env is passed
  os.environ['LOLA_ENV_TEST_PARENT'] = 'set in parent'

  with lola.Runner() as runner:
    out = runner.check_output(['test_scripts/env.py', 'LOLA_ENV_TEST_PARENT'],
                              env=env)

  expect(out) == 'not set'


def test_env_inherit_from_parent():
  # when "env" is not set explicitly this should be passed through
  os.environ['LOLA_ENV_TEST_PARENT'] = 'set in parent'

  with lola.Runner() as runner:
    out = runner.check_output(['test_scripts/env.py', 'LOLA_ENV_TEST_PARENT'])

  expect(out) == 'set in parent'


def test_reclose_throws_error():
  runner = lola.Runner()
  runner.close()

  with expect.raises(ValueError):
    runner.close()


def test_call_with_closed_runner_throws_error():
  runner = lola.Runner()
  runner.close()

  with expect.raises(ValueError):
    runner.call(['test_scripts/success.py'], stdout=DEVNULL, stderr=DEVNULL)


def test_with_block_closes_runner():
  with lola.Runner() as runner:
    pass

  with expect.raises(ValueError):
    runner.close()


def test_with_block_closes_runner_after_error():
  with expect.raises(KeyError):
    with lola.Runner() as runner:
      raise KeyError()

  with expect.raises(ValueError):
    runner.close()
