from collections import defaultdict


class FakeRedis:
    def __init__(self):
        self.data = {}
        self.sets = defaultdict(set)
        self.scan_calls = 0

    def get(self, key):
        return self.data.get(key)

    def setex(self, key, ttl, value):
        self.set(key, value)

    def set(self, key, value):
        self.data[key] = value

    def exists(self, key):
        return key in self.data

    def scan_iter(self, pattern):
        self.scan_calls += 1
        prefix = pattern.rstrip("*")
        return (key for key in list(self.data) if key.startswith(prefix))

    def smembers(self, key):
        return set(self.sets[key])

    def sadd(self, key, value):
        self.sets[key].add(value)

    def srem(self, key, value):
        self.sets[key].discard(value)

    def mget(self, keys):
        return [self.data.get(key) for key in keys]

    def pipeline(self):
        return FakePipeline(self)


class FakePipeline:
    def __init__(self, client):
        self.client = client
        self.commands = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def watch(self, key):
        pass

    def multi(self):
        pass

    def get(self, key):
        return self.client.get(key)

    def setex(self, key, ttl, value):
        self.commands.append((self.client.setex, (key, ttl, value)))

    def sadd(self, key, value):
        self.commands.append((self.client.sadd, (key, value)))

    def srem(self, key, value):
        self.commands.append((self.client.srem, (key, value)))

    def execute(self):
        return [command(*args) for command, args in self.commands]
