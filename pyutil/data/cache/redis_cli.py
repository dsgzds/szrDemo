# encoding:utf8

import json
import redis
from config import config


def create_redis_cli(server, db):
    host, port = server
    args = {
        "host": host,
        "port": int(port),
        "socket_timeout": 2,
        "db": db
    }
    pool = redis.BlockingConnectionPool(**args)
    return redis.StrictRedis(connection_pool=pool)

def_redis_cli = create_redis_cli((config.redis.host, config.redis.port), config.redis.db)


class CacheBase(object):

    def __init__(self, prefix='CACHE', sub_prefix='', expire=None):
        self.prefix = prefix
        self.sub_prefix = sub_prefix
        self.expire = expire

    def format_key(self, key):
        if not self.sub_prefix:
            return '%s|%s' % (self.prefix, key)

        return '%s|%s|%s' % (self.prefix, self.sub_prefix, key)

    def get_from_src(self, key):
        return

    def get(self, key):
        _key = self.format_key(key)
        value = def_redis_cli.get(_key)

        if not value:
            value = self.get_from_src(key)
        
            if value:
                self.set(key, value)

        if value and isinstance(value, (str, bytes)):
            try:
                value = json.loads(value)
            except:
                pass

        return value


    def set(self, key, value):
        _key = self.format_key(key)
        if isinstance(value, (dict, list)):
            value = json.dumps(value)

        def_redis_cli.set(_key, value, self.expire)


    def delete(self, key):
        _key = self.format_key(key)
        def_redis_cli.delete(_key)

    def refresh(self, key):
        _key = self.format_key(key)
        self.delete(key)
        delf.get(key)

