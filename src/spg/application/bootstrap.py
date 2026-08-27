"""Explicit application composition for the S1-A foundation."""

from dataclasses import dataclass

from spg.config import Settings
from spg.application.runtime import RuntimeService
from spg.application.preparation import PreparationService
from spg.application.execution import ExecutionService
from spg.infrastructure.persistence import Database


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

    def persistence(self) -> Database:
        """Compose persistence explicitly without affecting foundation status."""

        return Database.from_settings(self.settings)

    def runtime(self, database: Database | None = None) -> RuntimeService:
        """Compose governed Runtime operations over explicit persistence."""

        return RuntimeService(database or self.persistence())

    def preparation(self, database: Database | None = None) -> PreparationService:
        """Compose S2-A preparation without composing or dispatching an Executor."""

        return PreparationService(database or self.persistence())

    def execution(self, database: Database | None = None) -> ExecutionService:
        """Compose S2-B Runtime orchestration without selecting a real provider."""

        selected_database = database or self.persistence()
        preparation = PreparationService(selected_database)
        return ExecutionService(selected_database, preparation=preparation)


def bootstrap(settings: Settings | None = None) -> Application:
    """Construct the application explicitly from typed settings."""

    return Application(settings=settings or Settings())
