"""Executable event model, NOT a powerd implementation or hardware proof."""
from .calendar import local_day, wake_plan


class Simulator:
    def __init__(self, available, display_failures=0, rtc_failures=0):
        self.available = set(available)
        self.display_failures = display_failures
        self.rtc_failures = rtc_failures
        self.asleep = False
        self.displayed = None
        self.log = []

    def event(self, kind, now):
        if kind not in {"startup", "sleep", "resume", "midnight", "clock-change", "ready-to-suspend"}:
            raise ValueError("Evento desconocido")
        plan = wake_plan(now)
        if kind == "sleep":
            self.asleep = True
        elif kind in {"startup", "resume"}:
            self.asleep = False
        result = {"event": kind, "now": now.isoformat(), "plan": plan, "actions": []}
        actions = result["actions"]
        if kind == "ready-to-suspend":
            if self.asleep:
                for attempt in range(1, 4):
                    if self.rtc_failures:
                        self.rtc_failures -= 1
                        actions.append({"rtc_failure": attempt})
                    else:
                        actions.append({"arm": plan["next_midnight"]})
                        break
                else:
                    actions.append({"error": "rtc-unarmed"})
        elif self.asleep:
            day = local_day(now).isoformat()
            if day not in self.available:
                actions.append({"error": "missing-image", "date": day})
            else:
                for attempt in range(1, 4):
                    if self.display_failures:
                        self.display_failures -= 1
                        actions.append({"display_failure": attempt})
                    else:
                        self.displayed = day
                        actions.append({"display": day})
                        break
                else:
                    actions.append({"error": "display-failed"})
        else:
            actions.append({"skip": "reading"})
        self.log.append(result)
        return result
