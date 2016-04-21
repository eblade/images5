import threading
import bottle
import requests
import enum
import time


class Channel(object):
    def __init__(self, name):
        self.name = name
        self.lock = threading.Lock()
        self.messages = {}
        self.queue = threading.Queue()
        self.subscriptions = {}

    def get(self, key):
        assert key

        try:
            versions = self.messages[key]
            return versions.current
        except KeyError:
            raise KeyError("Key '%s' does not exist." % key)

    def create(self, message):
        assert message.key
        assert message.version == 1

        try:
            self.lock.acquire()
            if message.key in self.messages.keys():
                raise KeyError("Key '%s' already exists." % message.key)
            versions = MessageVersions()
            versions.current = message
            self.messages[message.key] = versions
        finally:
            self.lock.release()

    def subscribe(self, type, url):
        try:
            self.lock.acquire()
            self.subscriptions[url].type = type
        except KeyError:
            self.subscriptions[url] = Subscription(self.name, type, url)
        finally:
            self.lock.release()

    def unsubscribe(self, url):
        try:
            self.lock.acquire()
            del self.subscriptions[url]
        except KeyError:
            pass
        finally:
            self.lock.release()


class MessageStatus(enum.IntEnum):
    ok = 1
    pending = 2
    conflict = 3


class Message(object):
    def __init__(self, key, data, headers, version=1):
        self.key = key
        self.data = data
        self.version = version
        self.status = MessageStatus.pending
        self.headers = dict(headers)


class MessageVersions(object):
    def __init__(self):
        self.current = None
        self.pending = None


class SubscriptionType(enum.IntEnum):
    topic = 1
    queue = 2
    replication = 3


class Subscription(object):
    def __init__(self, channel, type, url):
        self.channel = channel
        self.type = SubscriptionType(type)
        self.url = url


class DBMQ(object):
    def __init__(self):
        self.channels = {}
        self.client_tokens = set()
        self.lock = threading.Lock()

    def get(self, channel, key):
        assert cilent_token in self.client_token
        assert channel_name
        assert key
        
        try:
            self.lock.acquire()
            channel = self.channels[channel_name]
            return channel.get(key)
        except KeyError:
            raise KeyError("Bad channel '%s'." % str(channel_name))
        finally:
            self.lock.release()

    def create(self, client_token, channel_name, key, headers, data):
        assert client_token in self.client_tokens
        assert channel_name
        assert key

        now = time.now()
        channel = None
        
        try:
            self.lock.acquire()
            channel = self.channels[channel_name]
        except KeyError:
            channel = Channel(channel_name)
            self.channels[channel_name] = channel
        finally:
            self.lock.release()

        if channel is None:
            raise KeyError("Bad channel '%s'." % str(channel_name))

        headers['Created-By'] = client_token
        headers['Created'] = now
        headers['Modified-By'] = client_token
        headers['Modified'] = now
        message = Message(key, data, headers)
        channel.create(message)

    def subscribe(self, channel_name, type, url):
        assert channel_name
        type = getattr(SubscriptionType, type)
        assert url

        channel = None

        try:
            self.lock.acquire()
            channel = self.channels[channel_name]
        except KeyError:
            channel = Channel(channel_name)
            self.channels[channel_name] = channel
        finally:
            self.lock.release()

        if channel is None:
            raise KeyError("Bad channel '%s'." % str(channel_name))

        channel.subscribe(type, url)

    def unsubscribe(self, channel_name, url):
        assert channel_name
        assert url

        try:
            self.lock.acquire()
            self.channels[channel_name].unsubscribe(url)
        except KeyError:
            pass
        finally:
            self.lock.release()


if __name__ == '__main__':
    dbmq = DBMQ()
    http = bottle.Bottle()
    
    dbmq.client_tokens.add('A')
    dbmq.client_tokens.add('B')
    dbmq.client_tokens.add('C')

    @http.get('/<channel>/<key>')
    def get(channel, key):
        client_token = bottle.headers.pop('Client-Token')
        dbmq.get(client_token, channel, key, headers, bottle.request.body.read())

    @http.post('/<channel>/<key>')
    def create(channel, key):
        client_token = bottle.headers.pop('Client-Token')
        headers = {k: v for k, v in bottle.headers.items() if k.startswith('X-')}
        dbmq.create(client_token, channel, key, headers, bottle.request.body.read())

    @http.put('/<channel>/<key>')
    def update(channel, key):
        client_token = bottle.headers.pop('Client-Token')
        source_version = bottle.headers.pop('Source-Version')
        headers = {k: v for k, v in bottle.headers.items() if k.startswith('X-')}
        dbmq.update(client_token, channel, key, headers, bottle.request.body.read())

    @http.delete('/<channel>/<key>')
    def delete(channel, key):
        client_token = bottle.headers.pop('Client-Token')
        source_version = bottle.headers.pop('Source-Version')
        headers = {k: v for k, v in bottle.headers.items() if k.startswith('X-')}
        dbmq.delete(client_token, channel, key, headers, bottle.request.body.read())

    @http.get('/<channel>')
    def subscribe(channel):
        dbmq.subscribe(channel, bottle.request.query.get('type'), bottle.request.query.get('url'))

    @http.delete('/<channel>')
    def unsubscribe(channel):
        dbmq.unsubscribe(channel, bottle.request.query.get('url'))

    bottle.debug(True)
    http.run()
