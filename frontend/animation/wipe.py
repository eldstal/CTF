from asciimatics.effects import Effect
from asciimatics.screen import Screen
from asciimatics.exceptions import NextScene

import math
import random

# Text and color lists
from frontend.animation.util import RAINBOW_256,RAINBOW_8,NOISE_DOS

class RainbowWipe(Effect):
    """
    Rapidly clears the screen with a rainbow wave of sparkles
    """

    def __init__(self, screen, duration, colors=None, **kwargs):
        """
        :param screen: The Screen being used for the Scene.
        :param duration: How many frames to complete the transition
        :param colors: List of color indices to cycle through. Default: Rainbow

        Also see the common keyword arguments in :py:obj:`.Effect`.
        """
        super(RainbowWipe, self).__init__(screen, **kwargs)
        self._duration = duration
        self._last_frame = None

        if colors is None:
            if screen.colours == 256:
                colors = RAINBOW_256
            else:
                colors = RAINBOW_8

        self._colors=colors


        self._thickness = 6
        self._angle = 2  # dx / dy

        # Swipe from one corner to the opposite one
        steps = screen.width + (self._angle * screen.height) + self._thickness
        self.frames_per_step = duration / steps

    def reset(self):
        pass

    @property
    def stop_frame(self):
        return self._duration

    def _update(self, frame_no):
        step = int(frame_no / self.frames_per_step)

        # Swipe from top-right to bottom-left, clearing the screen as we go

        H,W = self._screen.dimensions

        color = self._colors[step % len(self._colors)]

        # The colorful diagonal itself, including the trailing clear space
        for y in range(H):
            x = int(W- step + self._angle*y)
            text = "." * self._thickness

            # Clear everything to the right of this wave
            text += " " * (W - x - len(text))

            self.screen.print_at(text, x, y, colour=color, transparent=False)


class NoiseWipe(Effect):
    """
    Clears the screen with a vanishing cloud of cool DOS characters
    """

    def __init__(self, screen, duration, chars=None, colors=None, **kwargs):
        """
        :param screen: The Screen being used for the Scene.
        :param duration: How many frames to complete the transition
        :param colors: List of color indices to cycle through. Default: Rainbow

        Also see the common keyword arguments in :py:obj:`.Effect`.
        """
        super(NoiseWipe, self).__init__(screen, **kwargs)
        self._duration = duration
        self._last_frame = None

        if colors is None:
            if screen.colours == 256:
                colors = RAINBOW_256
            else:
                colors = RAINBOW_8

        if chars is None:
            chars = NOISE_DOS

        self._chars = chars
        self._colors = colors


        self._thickness = 6
        self._angle = 2  # dx / dy

        # Swipe from one corner to the opposite one
        steps = screen.width + (self._angle * screen.height) + self._thickness
        self.frames_per_step = duration / steps

        # Pass in 0.0 for start and 1.0 for end
        # Returns 1 for "Absolutely covered" and 0 for "Definitely not covered"
        self._time_density = lambda frame: 1 - abs(0.5 - frame)

        # Pass in 0,0 for top left and 1,1 for bottom-right
        # Returns a scaling 0-1 for how dense that location should be
        self._pos_density = lambda x,y: 1 - math.sqrt((x-0.5)**2 + (y-0.5)**2)


    def reset(self):
        pass

    @property
    def stop_frame(self):
        return self._duration

    def _update(self, frame_no):

        H,W = self._screen.dimensions

        progress = frame_no / self._duration
        td = self._time_density(progress)

        color = self._colors[ int(progress * len(self._colors) - 1)]

        # The colorful diagonal itself, including the trailing clear space
        for y in range(H):

            for x in range(W):
                rx = x / (W-1)
                ry = y / (H-1)

                pd = self._pos_density(rx, ry)

                dens = pd * td

                sample = random.random() * dens

                text = " "
                if (sample > 0.5):
                    text = random.choice(self._chars)

                # Toward the end of the animation, start overwriting with empty space
                # This makes the old text vanish with the noise cloud
                wipe = (pd*(1-progress)) < 0.3
                self.screen.print_at(text, x, y, colour=color, transparent=(not wipe))

        #if frame_no == self._duration:
        #    raise NextScene()
