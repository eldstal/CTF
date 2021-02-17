import queue
import time


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

        print("Configuration: ")
        for k,v in self.conf.items():
            print(f"  {k}: {v}")

    def run(self):
        while True:
            evt = self.events.get()
            msg,data = evt
            print(f"{msg}:  {data}"[:80])

    # An event from the middle-end about something that changed
    def handle_event(self, event):
        self.events.put(event)
