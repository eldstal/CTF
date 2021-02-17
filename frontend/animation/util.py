from asciimatics.effects import Effect
from asciimatics.screen import Screen

RAINBOW_256 = [ 160, 196, 202, 208, 214, 220, 226,
                192, 191, 190,120, 119, 118, 82, 46,
                49, 51, 45, 39, 33, 27, 21, 19, 55,
                56, 57, 128, 129, 165, 52, 88 ]
RAINBOW_8 = [
                Screen.COLOUR_RED,
                Screen.COLOUR_YELLOW,
                Screen.COLOUR_GREEN,
                Screen.COLOUR_CYAN,
                Screen.COLOUR_BLUE,
                Screen.COLOUR_MAGENTA,
            ]

# The cool characters from codepage 437
NOISE_DOS = (
             u"┤╡╢╖╕╣║╗╝╜╛┐└┴┬├─┼╞╟╚╔╩╦╠═╬╧╨╤╥╙╘╒╓╫╪┘┌" +
             u"αßΓπΣσµτΦΘΩδ∞φε" +
             u"☺☻♥♦♣♠•◘○◙♂♀♪♫☼►◄↕‼¶§▬↨↑↓→←∟↔▲▼" +
             u"∩≡±≥≤⌠⌡÷≈°∙·√ⁿ²■"
            )


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

