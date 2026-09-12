
from __future__ import annotations

import enum
from typing import Optional

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..backend.database import Base


class OSType(str, enum.Enum):
    QNX = "QNX"
    ANDROID_AUTOMOTIVE = "Android Automotive"
    LINUX_PROPRIETARY = "Linux (proprietary)"
    PROPRIETARY_RTOS = "Proprietary RTOS"
    MB_OS = "MB.OS (Mercedes-Benz)"
    CCNC = "ccNC (Hyundai Motor Group)"
    AOSP = "AOSP (Android Open Source Project, non-certified)"
    BMW_OS_X = "BMW Operating System X (Panoramic iDrive)"
    ARENE = "Arene (Woven by Toyota, SDV)"
    CHANGAN_OS = "Changan OS (EPA1, Deepal-derived)"
    OTHER = "Other"


class Manufacturer(Base):
    __tablename__ = "manufacturers"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), default=None)

    models: Mapped[list[CarModel]] = relationship(
        back_populates="manufacturer", cascade="all, delete-orphan"
    )


class CarModel(Base):
    __tablename__ = "car_models"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    manufacturer_id: Mapped[int] = mapped_column(ForeignKey("manufacturers.id"))
    name: Mapped[str] = mapped_column(String(150))
    model_year: Mapped[int]
    powertrain: Mapped[str] = mapped_column(String(50))

    manufacturer: Mapped[Manufacturer] = relationship(back_populates="models")
    infotainment: Mapped[Optional[InfotainmentSpec]] = relationship(
        back_populates="car_model", uselist=False, cascade="all, delete-orphan"
    )


class InfotainmentSpec(Base):
    __tablename__ = "infotainment_specs"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    car_model_id: Mapped[int] = mapped_column(ForeignKey("car_models.id"), unique=True)

    os_type: Mapped[OSType] = mapped_column(SAEnum(OSType))
    display_size_in: Mapped[float]
    display_resolution_px: Mapped[str] = mapped_column(String(20))
    physical_buttons_count: Mapped[int]

    voice_control: Mapped[bool] = mapped_column(default=False)
    ota_updates: Mapped[bool] = mapped_column(default=False)
    carplay_support: Mapped[bool] = mapped_column(default=False)
    android_auto_support: Mapped[bool] = mapped_column(default=False)
    personalization_profiles: Mapped[bool] = mapped_column(default=False)
    builtin_navigation: Mapped[bool] = mapped_column(default=False)
    smart_home_compat: Mapped[bool] = mapped_column(default=False)
    multimodal_input: Mapped[bool] = mapped_column(default=False)
    multi_zone_displays: Mapped[bool] = mapped_column(default=False)
    multi_bluetooth: Mapped[bool] = mapped_column(default=False)
    charging_route_integration: Mapped[bool] = mapped_column(default=False)

    startup_time_sec: Mapped[float]
    reaction_time_ms: Mapped[float]
    avg_steps_to_task: Mapped[float]

    ease_of_use_score: Mapped[float]
    ergonomics_score: Mapped[float]
    safety_distraction_score: Mapped[float]

    car_model: Mapped[CarModel] = relationship(back_populates="infotainment")

    COST_CRITERIA = {"startup_time_sec", "reaction_time_ms", "avg_steps_to_task"}
