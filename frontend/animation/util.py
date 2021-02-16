from asciimatics.effects import Effect
from asciimatics.screen import Screen


class ScreenShot(Effect):
    """
    Copies screen content on construction, displays it in a single frame on playback.
    """

    def __init__(self, screen, **kwargs):
        """
        :param screen: The Screen being used for the Scene.
        """
        super(ScreenShot, self).__init__(screen, **kwargs)

        # get_from doesn't support unicode, so this isn't perfect.
        # The proper solution is probably to have a Scene that we print to in the first place...?
        self._data = [ [ screen.get_from(x,y) for x in range(screen.width) ] for y in range(screen.height) ]

    def reset(self):
        pass

    @property
    def stop_frame(self):
        return 1

    def _update(self, frame_no):
        for y in range(self._screen.height):
            for x in range(self._screen.width):
                txt,fg,attr,bg = self._data[y][x]
                self._screen.print_at(chr(txt), x, y, fg, attr, bg, transparent=False)

