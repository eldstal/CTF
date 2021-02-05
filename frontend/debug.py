
# A frontend which only prints its events, nothing more
class FrontEnd:
    @staticmethod
    def help():
        return [
                 "options: none"
               ]

    def __init__(self, conf):
        self.conf = conf
        pass

    def start(self):
        pass

    def stop(self):
        pass

    # An event from the middle-end about something that changed
    def handle_event(self, event):
        msg,data = event
        print(f"{msg}:  {data}"[:80])
