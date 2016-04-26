import threading
import bottle
import requests
import enum
import time
import queue
import json


class ChannelError(bottle.HTTPError):
    def __init__(self, channel_name):
        super(ChanelError, self).__init__(400, 'Channel Error for "%s"' % channel_name)


class InvalidSecret(bottle.HTTPError):
    def __init__(self):
        super(InvalidSecret, self).__init__(401, 'Invalid Secret')


class InvalidToken(bottle.HTTPError):
    def __init__(self):
        super(InvalidToken, self).__init__(401, 'Invalid Token')


class MissingKey(bottle.HTTPError):
    def __init__(self, key):
        super(MissingKey, self).__init__(404, 'Missing Key "%s"' % key)


class KeyConflict(bottle.HTTPError):
    def __init__(self, key):
        super(KeyConflict, self).__init__(409, 'Key Conflict "%s"' % key)


class BadSubscriptionType(bottle.HTTPError):
    def __init__(self, type):
        super(BadSubscriptionType, self).__init__(400, 'Bad Subscription Type "%s"' % str(type))


class Channel(object):
    def __init__(self, name):
        self.name = name
        self.lock = threading.Lock()
        self.messages = {}
        self.queue = queue.Queue()
        self.subscriptions = {}
        self._cached_has_replicators = None
        self.worker = threading.Thread(target=self.pusher, name=name)
        self.worker.daemon = True
        self.worker.start()

    def to_string(self):
        result = 'Channel=%s\n' % self.name
        try:
            self.lock.acquire()
            for versions in self.messages.values():
                result += 'C:' + str(versions.current) + '\n'
                result += 'P:' + str(versions.pending) + '\n'
        finally:
            self.lock.release()
        return result

    def pusher(self):
        while True:
            message = self.queue.get()
            for subscription in self.subscriptions.values():
                requests.post(subscription.url, message.data)
            self.queue.task_done()

    def has_replicators(self):
        if self._cached_has_replicators is not None:
            return self._cached_has_replicators
        else:
            for subscription in self.subscriptions.values():
                if subscription.type == SubscriptionType.replication:
                    self._cached_has_replicators = True
                    return True
            self._cached_has_replicators = False
            return False

    def get(self, key):
        assert key

        try:
            versions = self.messages[key]
            if versions.current is None:
                raise MissingKey(key)
            return versions.current
        except KeyError:
            raise MissingKey(key)

    def create(self, message):
        assert message.key
        assert message.version == 1

        message.status = MessageStatus.ok
        try:
            self.lock.acquire()
            try:
                versions = self.messages[message.key]
            except KeyError:
                versions = MessageVersions()
            if versions.current is not None:
                raise KeyConflict(message.key)
            if versions.pending is not None:
                raise KeyConflict(message.key)

            versions.current = message
            self.messages[message.key] = versions
            self.queue.put(message)
        finally:
            self.lock.release()

    def update(self, message):
        assert message.key
        assert message.version
        assert message.status == MessageStatus.pending

        try:
            self.lock.acquire()
            try:
                versions = self.messages[message.key]
                if versions.current is None:
                    raise MissingKey(message.key)
                message.version = versions.current.version + 1
                if self.has_replicators():
                    versions.pending = message
                else:
                    message.status == MessageStatus.ok
                    versions.current = message
                self.queue.put(message)
            except KeyError:
                raise MissingKey(message.key)
        finally:
            self.lock.release()

    def delete(self, message):
        assert message.key
        assert message.version
        assert message.headers

        deleted = message.headers['Deleted']
        deleted_by = message.headers['Deleted-By']

        try:
            self.lock.acquire()
            try:
                versions = self.messages[message.key]

                if versions.current is None:
                    raise MissingKey(message.key)

                if versions.current.version != message.version:
                    raise InactiveVersion(message.key, message.version)

                versions.current.headers['Deleted'] = deleted
                versions.current.headers['Deleted-By'] = deleted_by
                versions.deleted = versions.current
                versions.current = None
            except KeyError:
                raise MissingKey(message.key)
        finally:
            self.lock.release()

    def subscribe(self, node_token, type, url):
        self._cached_has_replicators = None
        try:
            self.lock.acquire()
            self.subscriptions[node_token].type = type
        except KeyError:
            self.subscriptions[node_token] = Subscription(self.name, node_token, type, url)
        finally:
            self.lock.release()

    def unsubscribe(self, node_token):
        self._cached_has_replicators = None
        try:
            self.lock.acquire()
            del self.subscriptions[node_token]
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

    def __str__(self):
        return '<Message %s/%i "%s">' % (self.key, self.version, str(self.data, 'utf8'))


class MessageVersions(object):
    def __init__(self):
        self.current = None
        self.pending = None
        self.deleted = None


class SubscriptionType(enum.IntEnum):
    topic = 1
    queue = 2
    replication = 3


class Subscription(object):
    def __init__(self, channel, node_token, type, url):
        self.channel = channel
        self.node_token = node_token
        self.type = SubscriptionType(type)
        self.url = url
    
    def to_dict(self):
        return {
            'channel': self.channel,
            'token': self.node_token,
            'type': self.type.name,
            'url': self.url,
        }


class NodeType(enum.IntEnum):
    client = 1
    server = 2


class Node(object):
    def __init__(self, address, token, secret, type=NodeType.client):
        self.address = address  # really needed?
        self.token = token
        self.secret = secret


class DBMQ(object):
    def __init__(self):
        self.channels = {}
        self.nodes = {}
        self.lock = threading.Lock()

    def add_node(self, node):
        assert node.token
        assert node.address
        try:
            self.lock.acquire()
            self.nodes[node.token] = node
        finally:
            self.lock.release()

    def authenticate(self, node_token, node_secret):
        assert node_token
        assert node_secret
        node = self.nodes.get(node_token)

        if node is None:
            raise InvalidToken

        if node_secret != node.secret:
            raise InvalidSecret

    def get_channel(self, channel_name):
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
            raise ChannelError(channel_name)

        return channel

    def get(self, node_token, node_secret, channel_name, key, headers):
        self.authenticate(node_token, node_secret)
        assert channel_name
        assert key
        
        return self.get_channel(channel_name).get(key)

    def create(self, node_token, node_secret, channel_name, key, headers, data):
        self.authenticate(node_token, node_secret)
        assert channel_name
        assert key

        now = time.time()
        channel = self.get_channel(channel_name)

        headers['Created-By'] = node_token
        headers['Created'] = now
        headers['Modified-By'] = node_token
        headers['Modified'] = now
        message = Message(key, data, headers)
        channel.create(message)
        print(channel.to_string())

    def update(self, node_token, node_secret, channel_name, key, headers, data):
        self.authenticate(node_token, node_secret)
        assert channel_name
        assert key

        now = time.time()
        channel = self.get_channel(channel_name)

        headers['Modified-By'] = node_token
        headers['Modified'] = now
        message = Message(key, data, headers)
        channel.update(message)
        print(channel.to_string())

    def delete(self, node_token, node_secret, channel_name, key, headers):
        self.authenticate(node_token, node_secret)
        assert channel_name
        assert key

        now = time.time()
        channel = self.get_channel(channel_name)

        headers['Deleted-By'] = node_token
        headers['Deleted'] = now
        message = Message(key, None, headers)
        channel.delete(message)

    def subscribe(self, node_token, node_secret, channel_name, type, url):
        self.authenticate(node_token, node_secret)
        assert channel_name
        try :
            type = getattr(SubscriptionType, type)
        except AttributeError:
            raise BadSubscriptionType(type)
        except TypeError:
            raise BadSubscriptionType(type)
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

        channel.subscribe(node_token, type, url)

    def unsubscribe(self, node_token, node_secret, channel_name):
        self.authenticate(node_token, node_secret)
        assert channel_name

        try:
            self.lock.acquire()
            self.channels[channel_name].unsubscribe(node_token)
        except KeyError:
            pass
        finally:
            self.lock.release()

    def get_subscriptions(self, node_token, node_secret, channel_name):
        self.authenticate(node_token, node_secret)
        assert channel_name

        try:
            self.lock.acquire()
            return self.channels[channel_name].subscriptions
        except KeyError:
            raise ChannelError(channel_name)
        finally:
            self.lock.release()


if __name__ == '__main__':
    dbmq = DBMQ()
    http = bottle.Bottle()
    
    dbmq.add_node(Node('http://localhost:8080/', 'A', 'As')) # me
    dbmq.add_node(Node('http://localhost:8081/', 'a', 'as'))
    dbmq.add_node(Node('http://localhost:8082/', 'b', 'bs'))
    dbmq.add_node(Node('http://localhost:8083/', 'c', 'cs'))

    @http.route('/', 'HEAD')
    def check():
        raise bottle.HTTPResponse(status=204)

    @http.get('/<channel>/<key>')
    def get(channel, key):
        node_token = bottle.request.headers.get('Client-Token')
        node_secret = bottle.request.headers.get('Client-Secret')
        headers = {k: v for k, v in bottle.request.headers.items() if k.startswith('X-')}
        message = dbmq.get(node_token, node_secret, channel, key, headers)
        raise bottle.HTTPResponse(message.data, 200, dict(message.headers))

    @http.post('/<channel>/<key>')
    def create(channel, key):
        node_token = bottle.request.headers.get('Client-Token')
        node_secret = bottle.request.headers.get('Client-Secret')
        headers = {k: v for k, v in bottle.request.headers.items() if k.startswith('X-')}
        dbmq.create(node_token, node_secret, channel, key, headers, bottle.request.body.read())
        raise bottle.HTTPResponse(status=201)

    @http.put('/<channel>/<key>')
    def update(channel, key):
        node_token = bottle.request.headers.get('Client-Token')
        node_secret = bottle.request.headers.get('Client-Secret')
        source_version = bottle.request.headers.get('Source-Version')
        headers = {k: v for k, v in bottle.request.headers.items() if k.startswith('X-')}
        dbmq.update(node_token, node_secret, channel, key, headers, bottle.request.body.read())
        raise bottle.HTTPResponse(status=202)

    @http.delete('/<channel>/<key>')
    def delete(channel, key):
        node_token = bottle.request.headers.get('Client-Token')
        node_secret = bottle.request.headers.get('Client-Secret')
        source_version = bottle.request.headers.get('Source-Version')
        headers = {k: v for k, v in bottle.request.headers.items() if k.startswith('X-')}
        dbmq.delete(node_token, node_secret, channel, key, headers)
        raise bottle.HTTPResponse(status=204)

    @http.post('/<channel>')
    def subscribe(channel):
        node_token = bottle.request.headers.get('Client-Token')
        node_secret = bottle.request.headers.get('Client-Secret')
        subscription_type = bottle.request.headers.get('Subscription-Type')
        hook_url = bottle.request.headers.get('Hook')
        dbmq.subscribe(node_token, node_secret, channel, subscription_type, hook_url)
        raise bottle.HTTPResponse(status=201)

    @http.delete('/<channel>')
    def unsubscribe(channel):
        node_token = bottle.request.headers.get('Client-Token')
        node_secret = bottle.request.headers.get('Client-Secret')
        hook_url = bottle.request.headers.get('Hook')
        dbmq.unsubscribe(node_token, node_secret, channel)
        raise bottle.HTTPResponse(status=204)

    @http.get('/<channel>')
    def list_subscriptions(channel):
        node_token = bottle.request.headers.get('Client-Token')
        node_secret = bottle.request.headers.get('Client-Secret')
        data = dbmq.get_subscriptions(node_token, node_secret, channel)
        raise bottle.HTTPResponse(body=json.dumps(data, indent=2, sort_keys=True, default=lambda x: x.to_dict()), status=200)

    bottle.debug(True)
    http.run(port=8080)
