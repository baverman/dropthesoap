def cached_property(func):
    name = '_' + func.__name__
    def inner(self):
        try:
            return getattr(self, name)
        except AttributeError:
            pass

        result = func(self)
        setattr(self, name, result)
        return result

    return property(inner)