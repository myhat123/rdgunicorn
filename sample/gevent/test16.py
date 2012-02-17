from gevent.pywsgi import WSGIServer

def application(environ, start_response):
    status = '200 OK'
    body = 'Hello Cruel World!'

    headers = [
        ('Content-Type', 'text/html')
    ]

    start_response(status, headers)
    return [body]

WSGIServer(('', 8000), application).serve_forever()
