"""Explicit application composition for the S1-A foundation."""

from dataclasses import dataclass

from spg.config import Settings


@dataclass(frozen=True, slots=True)
class Application:
    """Minimal application container without external side effects."""

    settings: Settings

    def status(self) -> dict[str, str]:
        """Return foundation metadata without fabricating production state."""

        return {
            "application": self.settings.application_name,
            "foundation": "ready",
            "runtime_profile": self.settings.runtime_profile,
        }


def bootstrap(settings: Settings | None = None) -> Application:
    """Construct the application explicitly from typed settings."""

    return Application(settings=settings or Settings())

