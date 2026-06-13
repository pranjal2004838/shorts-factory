"""One Euro Filter for smoothing noisy face-tracking signals.

Reference: Casiez, Roussel & Vogel (2012), "1 Euro Filter: A Simple Speed-
based Low-pass Filter for Noisy Input in Interactive Systems".

The filter adapts its cutoff to the signal speed: it smooths heavily when
the subject is still (killing jitter) and loosens up during fast motion
(killing lag). This is what gives the crop a cinematic, butter-smooth feel
instead of a shaky or laggy follow.
"""
from __future__ import annotations

import math


class _LowPass:
    def __init__(self) -> None:
        self._prev: float | None = None

    def __call__(self, value: float, alpha: float) -> float:
        if self._prev is None:
            self._prev = value
        else:
            self._prev = alpha * value + (1.0 - alpha) * self._prev
        return self._prev

    @property
    def last(self) -> float | None:
        return self._prev


class OneEuroFilter:
    """Scalar One Euro Filter.

    Args:
        freq: nominal sampling frequency (Hz), typically the video fps.
        min_cutoff: lower bound on cutoff frequency; smaller = smoother.
        beta: speed coefficient; larger = more responsive to fast motion.
        d_cutoff: cutoff for the derivative low-pass.
    """

    def __init__(
        self,
        freq: float,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        d_cutoff: float = 1.0,
    ) -> None:
        if freq <= 0:
            raise ValueError("freq must be > 0")
        self.freq = freq
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.d_cutoff = d_cutoff
        self._x = _LowPass()
        self._dx = _LowPass()
        self._last_value: float | None = None

    @staticmethod
    def _alpha(cutoff: float, freq: float) -> float:
        tau = 1.0 / (2.0 * math.pi * cutoff)
        te = 1.0 / freq
        return 1.0 / (1.0 + tau / te)

    def __call__(self, value: float) -> float:
        if self._last_value is None:
            dx = 0.0
        else:
            dx = (value - self._last_value) * self.freq
        edx = self._dx(dx, self._alpha(self.d_cutoff, self.freq))
        cutoff = self.min_cutoff + self.beta * abs(edx)
        filtered = self._x(value, self._alpha(cutoff, self.freq))
        self._last_value = value
        return filtered
