import queue

# A frontend which only prints its events, nothing more
class FrontEnd:
    @staticmethod
    def help():
        return [
                 "options: none"
               ]

    @staticmethod
    def needs_main_thread():
        return False

    def __init__(self, conf):
        self.conf = conf
        self.events = queue.Queue()

    # This will be run in its own thread
    def run(self):
        while True:
            evt = self.events.get()
            # Do something with the data!

    # An event from the middle-end about something that changed
    def handle_event(self, event):
        self.events.put(event)
