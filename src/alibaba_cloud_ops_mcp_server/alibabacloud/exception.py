import sys
import json
import logging

logger = logging.getLogger(__name__)


class AcsException(Exception):
    msg_fmt = 'An unknown exception occurred.'
    status = 500
    code = 'InternalError'

    def __init__(self, **kwargs):
        self.kwargs = kwargs

        try:
            self.message = self.msg_fmt.format(**kwargs) if kwargs else self.msg_fmt
            if isinstance(self.message, str):
                self.message = self.message.rstrip('.') + '.'
        except KeyError:
            logger.exception(f'Exception in string format operation: {self.code}, {self.msg_fmt}, {kwargs}')
            for name, value in kwargs.items():
                logger.error(f'{name}: {value}')

    def __str__(self):
        body = {
            'Message': self.message,
            'Code': self.code
        }
        return json.dumps(body)

    def __deepcopy__(self, memo):
        return self.__class__(**self.kwargs)

    def __unicode__(self):
        body = {
            'Message': self.message,
            'Code': self.code
        }
        return json.dumps(body)


class OOSExecutionFailed(AcsException):
    msg_fmt = 'OOS Execution Failed, reason: {reason}.'
    status = 400
    code = 'Execution.Failed'
