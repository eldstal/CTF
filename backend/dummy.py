from copy import deepcopy as CP

class BackEnd:

    @staticmethod
    def help():
        return [
            "url: none",
            "auth: none",
            "poll-interval: seconds",
        ]

    @staticmethod
    def supports(conf, url):
        # Return True if the url seems like a system we support
        return False

    def __init__(self, conf, middleend):
        self.conf = conf
        self.middle = middleend



    def run(self):
        pass

    def stop(self):
        pass

    def update(self):
        pass
