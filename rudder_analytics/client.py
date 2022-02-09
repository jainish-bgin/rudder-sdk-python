from datetime import datetime
from uuid import uuid4
import logging
import numbers
import atexit

from dateutil.tz import tzutc
from six import string_types

from rudder_analytics.utils import guess_timezone, clean
from rudder_analytics.consumer import Consumer
from rudder_analytics.request import post
from rudder_analytics.version import VERSION

try:
    import queue
except ImportError:
    import Queue as queue


ID_TYPES = (numbers.Number, string_types)

class Client(object):
    """Create a new Rudder client."""
    log = logging.getLogger('rudder')
    anonymoys_id = str(uuid4())

    def __init__(self, write_key=None, host='https://hosted.rudderlabs.com', debug=False,
                 max_queue_size=10000, send=True, on_error=None, flush_at=100,
                 flush_interval=0.5, max_retries=3, sync_mode=False,
                 timeout=15, thread=1):
        require('write_key', write_key, string_types)

        self.queue = queue.Queue(max_queue_size)
        self.write_key = write_key
        self.on_error = on_error
        self.debug = debug
        self.send = send
        self.sync_mode = sync_mode
        self.host = host
        self.timeout = timeout

        if debug:
            self.log.setLevel(logging.DEBUG)

        if sync_mode:
            self.consumers = None
        else:
            # On program exit, allow the consumer thread to exit cleanly.
            # This prevents exceptions and a messy shutdown when the
            # interpreter is destroyed before the daemon thread finishes
            # execution. However, it is *not* the same as flushing the queue!
            # To guarantee all messages have been delivered, you'll still need
            # to call flush().
            if send:
                atexit.register(self.join)
            for n in range(thread):
                self.consumers = []
                consumer = Consumer(
                    self.queue, write_key, host=host, on_error=on_error,
                    flush_at=flush_at, flush_interval=flush_interval,
                    retries=max_retries, timeout=timeout,
                )
                self.consumers.append(consumer)

                # if we've disabled sending, just don't start the consumer
                if send:
                    consumer.start()

    def identify(self, user_id=None, traits=None, context=None, timestamp=None,
                 anonymous_id=None, integrations=None, message_id=None):
        traits = traits or {}
        context = context or {}
        integrations = integrations or {}
        require('user_id or anonymous_id', user_id or anonymous_id, ID_TYPES)
        require('traits', traits, dict)

       

        msg = {
            'integrations': integrations,
            'anonymousId': anonymous_id,
            'timestamp': timestamp,
            'context': context,
            'type': 'identify',
            'userId': user_id,
            'traits': traits,
            'messageId': message_id,
        }

        return self._enqueue(msg)

    def track(self, user_id=None, event=None, properties=None, context=None,
              timestamp=None, anonymous_id=None, integrations=None,
              message_id=None):
        properties = properties or {}
        context = context or {}
        integrations = integrations or {}
        require('user_id or anonymous_id', user_id or anonymous_id, ID_TYPES)
        require('properties', properties, dict)
        require('event', event, string_types)

        msg = {
            'integrations': integrations,
            'anonymousId': anonymous_id,
            'properties': properties,
            'timestamp': timestamp,
            'context': context,
            'userId': user_id,
            'type': 'track',
            'event': event,
            'messageId': message_id,
        }

        return self._enqueue(msg)

    def alias(self, previous_id=None, user_id=None, context=None,
              timestamp=None, integrations=None, message_id=None):
        context = context or {}
        integrations = integrations or {}
        require('previous_id', previous_id, ID_TYPES)
        require('user_id', user_id, ID_TYPES)

        msg = {
            'integrations': integrations,
            'previousId': previous_id,
            'timestamp': timestamp,
            'context': context,
            'userId': user_id,
            'type': 'alias',
            'messageId': message_id,
        }

        return self._enqueue(msg)

    def group(self, user_id=None, group_id=None, traits=None, context=None,
              timestamp=None, anonymous_id=None, integrations=None,
              message_id=None):
        traits = traits or {}
        context = context or {}
        integrations = integrations or {}
        require('user_id or anonymous_id', user_id or anonymous_id, ID_TYPES)
        require('group_id', group_id, ID_TYPES)
        require('traits', traits, dict)

        msg = {
            'integrations': integrations,
            'anonymousId': anonymous_id,
            'timestamp': timestamp,
            'groupId': group_id,
            'context': context,
            'userId': user_id,
            'traits': traits,
            'type': 'group',
            'messageId': message_id,
        }

        return self._enqueue(msg)

    def page(self, user_id=None, category=None, name=None, properties=None,
             context=None, timestamp=None, anonymous_id=None,
             integrations=None, message_id=None):
        properties = properties or {}
        context = context or {}
        integrations = integrations or {}
        require('user_id or anonymous_id', user_id or anonymous_id, ID_TYPES)
        require('properties', properties, dict)

        if name:
            require('name', name, string_types)
        if category:
            require('category', category, string_types)

        msg = {
            'integrations': integrations,
            'anonymousId': anonymous_id,
            'properties': properties,
            'timestamp': timestamp,
            'category': category,
            'context': context,
            'userId': user_id,
            'type': 'page',
            'name': name,
            'messageId': message_id,
        }

        return self._enqueue(msg)

    def screen(self, user_id=None, category=None, name=None, properties=None,
               context=None, timestamp=None, anonymous_id=None,
               integrations=None, message_id=None):
        properties = properties or {}
        context = context or {}
        integrations = integrations or {}
        require('user_id or anonymous_id', user_id or anonymous_id, ID_TYPES)
        require('properties', properties, dict)

        if name:
            require('name', name, string_types)
        if category:
            require('category', category, string_types)

        msg = {
            'integrations': integrations,
            'anonymousId': anonymous_id,
            'properties': properties,
            'timestamp': timestamp,
            'category': category,
            'context': context,
            'userId': user_id,
            'type': 'screen',
            'name': name,
            'messageId': message_id,
        }

        return self._enqueue(msg)

    def _enqueue(self, msg):
        """Push a new `msg` onto the queue, return `(success, msg)`"""
        timestamp = msg['timestamp']
        if timestamp is None:
            timestamp = datetime.utcnow().replace(tzinfo=tzutc())
        message_id = msg.get('messageId')
        if message_id is None:
            message_id = uuid4()

        require('integrations', msg['integrations'], dict)
        require('type', msg['type'], string_types)
        require('timestamp', timestamp, datetime)
        require('context', msg['context'], dict)

        # add anonymousId to the message if not passed
        # anonymous id need not be forced.
        # msg['anonymousId'] = msg['anonymousId'] or self.anonymoys_id

        
        # add common
        timestamp = guess_timezone(timestamp)
        msg['timestamp'] = timestamp.isoformat()
        msg['messageId'] = stringify_id(message_id)
        msg['context']['library'] = {
            'name': 'rudder-analytics-python',
            'version': VERSION
        }

        msg['userId'] = stringify_id(msg.get('userId', None))
        msg['anonymousId'] = stringify_id(msg.get('anonymousId', None))

        msg = clean(msg)
        self.log.debug('queueing: %s', msg)

        # if send is False, return msg as if it was successfully queued
        if not self.send:
            return True, msg

        if self.sync_mode:
            self.log.debug('enqueued with blocking %s.', msg['type'])
            post(self.write_key, self.host, timeout=self.timeout, batch=[msg])

            return True, msg

        try:
            self.queue.put(msg, block=False)
            self.log.debug('enqueued %s.', msg['type'])
            return True, msg
        except queue.Full:
            self.log.warning('rudder-analytics-python queue is full')
            return False, msg

    def flush(self):
        """Forces a flush from the internal queue to the server"""
        queue = self.queue
        size = queue.qsize()
        queue.join()
        # Note that this message may not be precise, because of threading.
        self.log.debug('successfully flushed about %s items.', size)

    def join(self):
        """Ends the consumer thread once the queue is empty.
        Blocks execution until finished
        """
        for consumer in self.consumers:
            consumer.pause()
            try:
                consumer.join()
            except RuntimeError:
                # consumer thread has not started
                pass

    def shutdown(self):
        """Flush all messages and cleanly shutdown the client"""
        self.flush()
        self.join()


def require(name, field, data_type):
    """Require that the named `field` has the right `data_type`"""
    if not isinstance(field, data_type):
        msg = '{0} must have {1}, got: {2}'.format(name, data_type, field)
        raise AssertionError(msg)


def stringify_id(val):
    if val is None:
        return None
    if isinstance(val, string_types):
        return val
    return str(val)
