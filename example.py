#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dropthesoap.wsgi import Application
from dropthesoap.service import Service
from dropthesoap.schema import xs

service = Service('Adder', 'http://github.com/baverman/Adder/')

@service.expose(returns=xs.int)
def add(x=xs.int, y=xs.int):
    return x + y

app = Application(service, '/')
app.run()