"""Synthetic one-compartment IV-bolus exposure, version 0.1."""
from dataclasses import dataclass
import math

@dataclass(frozen=True)
class Regimen:
    dose_mg: float
    volume_l: float
    half_life_h: float
    interval_h: float
    count: int

    def __post_init__(self):
        for value in (self.dose_mg, self.volume_l, self.half_life_h, self.interval_h):
            if not math.isfinite(value) or value <= 0:
                raise ValueError("剂量、容积、半衰期和间隔必须为有限正数。")
        if type(self.count) is not int or not 1 <= self.count <= 1000:
            raise ValueError("次数必须为 1 到 1000 的整数。")
        if not math.isfinite(self.dose_mg / self.volume_l * self.count):
            raise ValueError("参数超出数值范围。")
        if not math.isfinite(self.interval_h * self.count):
            raise ValueError("时间轴超出数值范围。")

def concentration(regimen: Regimen, time_h: float) -> float:
    """Post-dose concentration in mg/L at an exact dose-event time."""
    if not math.isfinite(time_h) or time_h < 0:
        raise ValueError("时间必须为有限非负数。")
    total = 0.0
    for index in range(regimen.count):
        elapsed = time_h - index * regimen.interval_h
        if elapsed >= 0:
            total += regimen.dose_mg / regimen.volume_l * math.exp(
                -math.log(2) * (elapsed / regimen.half_life_h))
    return total
