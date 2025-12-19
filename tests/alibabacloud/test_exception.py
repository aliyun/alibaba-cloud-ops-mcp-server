import pytest
from alibaba_cloud_ops_mcp_server.alibabacloud import exception

def test_acs_exception_default():
    e = exception.AcsException()
    s = str(e)
    assert 'InternalError' in s
    assert 'unknown exception' in s.lower()
    assert e.status == 500
    assert e.code == 'InternalError'
    assert isinstance(e.__deepcopy__({}), exception.AcsException)
    assert isinstance(e.__unicode__(), str)

def test_acs_exception_format():
    class CustomEx(exception.AcsException):
        msg_fmt = 'Error: {foo}.'
        code = 'CustomError'
    e = CustomEx(foo='bar')
    assert 'bar' in str(e)
    assert 'CustomError' in str(e)

def test_acs_exception_format_keyerror(caplog):
    class CustomEx(exception.AcsException):
        msg_fmt = 'Error: {foo}.'
        code = 'CustomError'
    with caplog.at_level('ERROR'):
        e = CustomEx(badkey='baz')
        assert 'badkey' in caplog.text

def test_oos_execution_failed():
    e = exception.OOSExecutionFailed(reason='fail')
    s = str(e)
    assert 'OOS Execution Failed' in s
    assert 'Execution.Failed' in s
    assert e.status == 400
    assert e.code == 'Execution.Failed' 