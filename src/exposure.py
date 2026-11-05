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
    # Finite geometric sum, O(1), including the newest administered bolus.
    count = (regimen.count if time_h >= (regimen.count - 1) * regimen.interval_h
             else min(regimen.count, int(time_h / regimen.interval_h) + 1))
    while count > 0 and (count - 1) * regimen.interval_h > time_h:
        count -= 1
    while count < regimen.count and count * regimen.interval_h <= time_h:
        count += 1
    elapsed = time_h - (count - 1) * regimen.interval_h
    decay = math.log(2) * (regimen.interval_h / regimen.half_life_h)
    accumulation = count if decay == 0 else -math.expm1(-count * decay) / -math.expm1(-decay)
    return (regimen.dose_mg / regimen.volume_l) * accumulation * math.exp(
        -math.log(2) * (elapsed / regimen.half_life_h))
