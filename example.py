#!/usr/bin/env python
# -*- coding: utf-8 -*-

from dropthesoap.wsgi import Application
from dropthesoap.service import Service
from dropthesoap.schema import xs

service = Service('Adder', 'http://github.com/baverman/Adder/')


@service.expose(response=xs.int)
def add(x=xs.int, y=xs.int):
    return x + y


@service.expose(response=xs.int)
def exc(x=xs.int, y=xs.int):
    raise Exception('Boo')


app = Application(service)
print 'http://localhost:8000/?wsdl'
app.run()
