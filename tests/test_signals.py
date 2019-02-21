import time
from unittest import mock

import pytest

from edp import signalslib


@pytest.mark.parametrize(('signature', 'result'), [
    ({}, True),
    ({'bar': str}, False),
])
def test_check_signature_no_args(signature, result):
    def foo(): pass

    assert signalslib.check_signature(foo, signature) == result


@pytest.mark.parametrize(('signature', 'result'), [
    ({}, True),
    ({'bar': str}, False),
    ({'bar': None}, False),
    ({'baz': str}, False),
])
def test_check_signature_arg_no_annotation(signature, result):
    def foo(bar): pass

    assert signalslib.check_signature(foo, signature) == result


@pytest.mark.parametrize(('signature', 'result'), [
    ({}, True),
    ({'bar': str}, True),
    ({'bar': int}, False),
    ({'bar': str, 'test': int}, True),
    ({'bar': str, 'test': str}, False),
    ({'bar': str, 'test': int, 'baz': None}, False),
])
def test_check_signature_some_args(signature, result):
    def foo(bar: str, baz, test: int): pass

    assert signalslib.check_signature(foo, signature) == result


@pytest.mark.parametrize(('signature', 'result'), [
    ({}, True),
    ({'bar': str}, False)
])
def test_signal_bind_func_no_args(signature, result):
    def foo():
        pass

    signal = signalslib.Signal('test', **signature)

    try:
        signal.bind(foo)
    except TypeError:
        if result:
            raise AssertionError('Function was not binded')
    else:
        if not result:
            raise AssertionError('Function was binded')


@pytest.mark.parametrize(('signature', 'result'), [
    ({}, True),
    ({'bar': str}, False),
    ({'bar': None}, False),
    ({'baz': str}, False),
])
def test_signal_bind_func_arg_no_annotation(signature, result):
    def foo(bar):
        pass

    signal = signalslib.Signal('test', **signature)

    try:
        signal.bind(foo)
    except TypeError:
        if result:
            raise AssertionError('Function was not binded')
    else:
        if not result:
            raise AssertionError('Function was binded')


@pytest.mark.parametrize(('signature', 'result'), [
    ({}, True),
    ({'bar': str}, True),
    ({'bar': int}, False),
    ({'bar': str, 'test': int}, True),
    ({'bar': str, 'test': str}, False),
    ({'bar': str, 'test': int, 'baz': None}, False),
])
def test_signal_bind_func_some_args(signature, result):
    def foo(bar: str, baz, test: int):
        pass

    signal = signalslib.Signal('test', **signature)

    try:
        signal.bind(foo)
    except TypeError:
        if result:
            raise AssertionError('Function was not binded')
    else:
        if not result:
            raise AssertionError('Function was binded')


def test_signal_bind_as_decor():
    signal = signalslib.Signal('test')

    @signal.bind
    def foo(): pass

    assert foo in signal.callbacks


def test_signal_emit():
    def foo(): pass

    signal = signalslib.Signal('test')
    signal.bind(foo)

    with mock.patch('edp.signalslib.signal_manager') as signal_manager_mock:
        signal.emit()

    signal_manager_mock.emit.assert_called_once_with(signal)


@pytest.mark.parametrize('data', [
    {'baz': 1},
    {'baz': '1', 'bar': '1'},
])
def test_signal_emit_unmatching_data_signature(data):
    def foo(baz: str, bar): pass

    signal = signalslib.Signal('test', baz=str)
    signal.bind(foo)

    with mock.patch('edp.signalslib.signal_manager') as signal_manager_mock:
        with pytest.raises(TypeError):
            signal.emit(**data)


def test_execute_signal_item():
    callback1 = mock.MagicMock()
    callback1.side_effect = ValueError
    callback2 = mock.MagicMock()

    signal_item = signalslib.SignalExecutionItem('test', [callback1, callback2], {})
    signalslib.execute_signal_item(signal_item)

    callback1.assert_called_once_with()
    callback2.assert_called_once_with()


def test_signal_execution_e2e():
    mock_func = mock.MagicMock()

    def test_func(foo: str, bar: int):
        mock_func(foo=foo, bar=bar)

    signal = signalslib.Signal('test', foo=str, bar=int)
    signal.bind(test_func)

    with signalslib.signal_manager.get_signal_executor_thread():
        time.sleep(0.5)
        signal.emit(foo='test', bar=1)
        time.sleep(1)

    mock_func.assert_called_once_with(foo='test', bar=1)


def test_signal_bind_nonstrict():
    m = mock.MagicMock()
    signal = signalslib.Signal('Test', foo=dict)
    signal.bind_nonstrict(m)


def test_signal_emit_eager():
    m = mock.MagicMock()
    signal = signalslib.Signal('Test', test=str)
    signal.bind_nonstrict(m)

    signal.emit_eager(test='test')

    m.assert_called_once_with(test='test')
