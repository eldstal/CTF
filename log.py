from logging import StreamHandler

# Log handler which formats the
# message and calls a function
class FuncHandler(StreamHandler):

    def __init__(self):
        StreamHandler.__init__(self)
        self.functions = []

    def add_func(self, func):
        self.functions.append(func)

    def emit(self, record):
        txt = self.format(record)
        #print("Handler: " + txt)
        for f in self.functions:
            f(txt)
