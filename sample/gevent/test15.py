from gevent import Greenlet

env = {}

def run_code(code, env={}):
    local = locals()
    local.update(env)
    exec(code, globals(), local)
    return local

while True:
    code = raw_input('>')

    g = Greenlet.spawn(run_code, code, env)
    g.join() # block until code executes

    # If succesfull then pass the locals to the next command
    if g.value:
        env = g.get()
    else:
        print g.exception

