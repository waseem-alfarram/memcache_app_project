from collections import OrderedDict
import sys, base64, os, random

class Cache:
    def __init__(self, capacity, replacement_policy):
        self.data = OrderedDict()
        self.capacity = capacity * 1000000
        self.replacement_policy = replacement_policy


    def size(self):
        return sys.getsizeof(self.data)


    def encode(self, value):
        UPLOAD_FOLDER = 'static/destination_images/'
        cwd = os.path.join(UPLOAD_FOLDER, value)
        with open(cwd, "rb") as image:
            return base64.b64encode(image.read())


    def put(self, key, value):
        if self.size() >= self.capacity:
            self.freeUp()
        ext = os.path.splitext(value)[1][1:]
        self.data[key] = [self.encode(value), ext]
        if self.replacement_policy == "least-recently-used":
            self.data.move_to_end(key)


    def get(self, key):
        self.data.move_to_end(key)
        return self.data[key]


    def clear(self):
        self.data.clear()


    def invalidateKey(self, key):
        del self.data[key]


    def refreshConfiguration(self, capacity, replacement_policy):
        self.capacity = capacity
        self.replacement_policy = replacement_policy


    def randomReplacement(self):
        keys = list(self.data.keys())
        randomKey = random.choice(keys)
        self.invalidateKey(randomKey)


    def lruReplacement(self):
        self.data.popitem(last = False)


    def freeUp(self):
        if self.replacement_policy == "random-replacement":
            self.randomReplacement()
        else:
            self.lruReplacement()


    def length(self):
        return len(self.data)
