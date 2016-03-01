import os
import bottle


class App:
    BASE = '/'
    HTML = 'web'
    JS = os.path.join(HTML, 'js')
    CSS = os.path.join(HTML, 'css')
    
    @classmethod
    def create(self):
        app = bottle.Bottle()
        
        # Static files
        app.route(
            path='/',
            callback=lambda: bottle.static_file('index.html', root=self.HTML),
        )
        app.route(
            path='/js/<fn>.js',
            callback=lambda fn: bottle.static_file(fn + '.js', root=self.JS),
        )
        app.route(
            path='/css/<fn>.css',
            callback=lambda fn: bottle.static_file(fn + '.css', root=self.CSS),
        )

        return app


def Create(function, InputClass, pre=None):
    def f():
        if callable(pre):
            pre()
        o = InputClass.FromDict(bottle.request.json)
        print(o.to_json())
        if o is None:
            raise bottle.HTTPError(400)
        result = function(o)
        return result.to_json()
    return f


def Fetch(function, pre=None):
    def f():
        if callable(pre):
            pre()
        result = function()
        return result.to_json()
    return f


def FetchById(function, pre=None):
    def f(id):
        if callable(pre):
            pre()
        if id is None:
            raise bottle.HTTPError(400)
        result = function(id)
        return result.to_json()
    return f


def FetchByKey(function, pre=None):
    def f(key):
        if callable(pre):
            pre()
        if key is None:
            raise bottle.HTTPError(400)
        result = function(key)
        return result.to_json()
    return f


def FetchByQuery(function, QueryClass=None, pre=None):
    def f():
        if callable(pre):
            pre()
        if QueryClass is None:
            result = function()
        else:
            q = QueryClass.FromRequest()
            result = function(q)
        return result.to_json()
    return f


def UpdateById(function, InputClass, pre=None):
    def f(id):
        if callable(pre):
            pre()
        o = InputClass.FromDict(bottle.request.json)
        if o is None:
            raise bottle.HTTPError(400)
        result = function(id, o)
        return result.to_json()
    return f


def DeleteById(function, pre=None):
    def f(id):
        if callable(pre):
            pre()
        if id is None:
            raise bottle.HTTPError(400)
        function(id)
        raise bottle.HTTPError(204)
    return f


