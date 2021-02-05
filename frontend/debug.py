
# A frontend which only prints its events, nothing more
class FrontEnd:

    def __init__(self):
        pass

    # An event from the middle-end about something that changed
    def handle_event(self, event):
        print(event)
