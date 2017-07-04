
import sys
sys.path += ["."]  # Python 3 hack

from nose.tools import assert_equal, assert_not_equal, assert_raises, assert_true, assert_is
from numpy.testing.utils import assert_almost_equal
from Util import *
import numpy as np

import better_exchook
better_exchook.replace_traceback_format_tb()


def test_cmd_true():
  r = cmd("true")
  assert_equal(r, [])


def test_cmd_false():
  assert_raises(CalledProcessError, lambda: cmd("false"))


def test_cmd_stdout():
  r = cmd("echo 1; echo 2;")
  assert_equal(r, ["1", "2"])


def test_cmd_stderr():
  r = cmd("echo x >/dev/stderr")
  assert_equal(r, [], "cmd() output should only cover stdout")


def test_uniq():
  assert (uniq(np.array([0, 1, 1, 1, 2, 2])) == np.array([0, 1, 2])).all()


def test_slice_pad_zeros():
  assert_equal(list(slice_pad_zeros(np.array([1, 2, 3, 4]), begin=1, end=3)), [2, 3])
  assert_equal(list(slice_pad_zeros(np.array([1, 2, 3, 4]), begin=-2, end=2)), [0, 0, 1, 2])
  assert_equal(list(slice_pad_zeros(np.array([1, 2, 3, 4]), begin=-2, end=6)), [0, 0, 1, 2, 3, 4, 0, 0])
  assert_equal(list(slice_pad_zeros(np.array([1, 2, 3, 4]), begin=2, end=6)), [3, 4, 0, 0])


def test_parse_orthography_into_symbols():
  assert_equal(list("hi"), parse_orthography_into_symbols("hi"))
  assert_equal(list(" hello "), parse_orthography_into_symbols(" hello "))
  assert_equal(list("  "), parse_orthography_into_symbols("  "))
  assert_equal(list("hello ") + ["[FOO]"] + list(" bar "), parse_orthography_into_symbols("hello [FOO] bar "))


def test_parse_orthography():
  assert_equal(list("hi ") + ["[HES]"] + list(" there") + ["[END]"], parse_orthography("hi [HES] there "))


def test_NumbersDict_minus_1():
  a = NumbersDict({'classes': 11, 'data': 11})
  b = NumbersDict(10)
  r = a - b
  print(a, b, r)
  assert_equal(r, NumbersDict(numbers_dict={'classes': 1, 'data': 1}, broadcast_value=-10))


def test_NumbersDict_eq_1():
  a = NumbersDict({'classes': 11, 'data': 11})
  b = NumbersDict(11)
  r1 = a.elem_eq(b, result_with_default=False)
  r2 = a.elem_eq(b, result_with_default=True)
  r2a = a == b
  print(a, b, r1, r2, r2a)
  assert_is(all(r2.values()), r2a)
  assert_is(r1.value, None)
  assert_equal(r1.dict, {'classes': True, 'data': True})
  assert_equal(r1, NumbersDict({'classes': True, 'data': True}))
  assert_is(r2.value, None)
  assert_equal(r2.dict, {"classes": True, "data": True})
  assert_true(r2a)


def test_NumbersDict_eq_2():
  a = NumbersDict(10)
  assert_equal(a, 10)
  assert_not_equal(a, 5)


def test_NumbersDict_mul():
  a = NumbersDict(numbers_dict={"data": 3, "classes": 2}, broadcast_value=1)
  b = a * 2
  assert isinstance(b, NumbersDict)
  assert b.value == 2
  assert_equal(b.dict, {"data": 6, "classes": 4})


def test_NumbersDict_float_div():
  a = NumbersDict(numbers_dict={"data": 3.0, "classes": 2.0}, broadcast_value=1.0)
  b = a / 2.0
  assert isinstance(b, NumbersDict)
  assert_almost_equal(b.value, 0.5)
  assert_equal(list(sorted(b.dict.keys())), ["classes", "data"])
  assert_almost_equal(b.dict["data"], 1.5)
  assert_almost_equal(b.dict["classes"], 1.0)


def test_NumbersDict_int_floordiv():
  a = NumbersDict(numbers_dict={"data": 3, "classes": 2}, broadcast_value=1)
  b = a // 2
  assert isinstance(b, NumbersDict)
  assert_equal(b.value, 0)
  assert_equal(list(sorted(b.dict.keys())), ["classes", "data"])
  assert_equal(b.dict["data"], 1)
  assert_equal(b.dict["classes"], 1)


def test_collect_class_init_kwargs():
  class A(object):
    def __init__(self, a):
      pass
  class B(A):
    def __init__(self, b, **kwargs):
      super(B, self).__init__(**kwargs)
      pass
  class C(B):
    def __init__(self, b, c, **kwargs):
      super(C, self).__init__(**kwargs)
      pass

  kwargs = collect_class_init_kwargs(C)
  print(kwargs)
  assert_equal(sorted(kwargs), ["a", "b", "c"])


def test_terminal_size():
  terminal_size()


def test_try_get_caller_name():
  def sub():
    return try_get_caller_name()
  assert_equal(sub(), "test_try_get_caller_name")


def test_camel_case_to_snake_case():
  assert_equal(camel_case_to_snake_case("CamelCaseOp"), "camel_case_op")
