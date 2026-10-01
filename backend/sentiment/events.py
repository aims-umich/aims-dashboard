"""The lab's fixed list of widely covered nuclear-energy news, used to annotate the Events page.

Events are chosen from wire coverage before looking at any sentiment data, so the list is not tuned to the
spikes it lines up with. Spikes the list misses are found by `sentiment.api.queries.spikes` instead.
Add an event here and it appears on the site at the next API cache refresh. No migration is needed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True, slots=True)
class Event:
    day: date
    title: str

    @property
    def month(self) -> str:
        return self.day.strftime("%Y-%m")


EVENTS: tuple[Event, ...] = (
    Event(date(2022, 3, 4), "Russian forces seize the Zaporizhzhia nuclear plant"),
    Event(date(2022, 8, 5), "Shelling around Zaporizhzhia, IAEA warns of disaster"),
    Event(date(2022, 12, 13), "Fusion ignition at the National Ignition Facility"),
    Event(date(2023, 4, 15), "Germany shuts down its last three reactors"),
    Event(date(2023, 8, 24), "Fukushima treated-water release begins"),
    Event(date(2024, 3, 21), "First Nuclear Energy Summit in Brussels"),
    Event(date(2024, 9, 20), "Deal to restart Three Mile Island Unit 1 for Microsoft"),
    Event(date(2024, 10, 14), "Google signs a small-reactor deal with Kairos Power"),
    Event(date(2025, 5, 23), "U.S. executive orders to quadruple nuclear power"),
)
