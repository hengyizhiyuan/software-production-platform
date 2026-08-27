"""Small explicit SQLAlchemy transaction boundary."""

from types import TracebackType

from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.orm.session import SessionTransaction


class UnitOfWork:
    """Own one Session and local transaction, requiring an explicit commit."""

    def __init__(self, session_factory: sessionmaker[Session]) -> None:
        self._session_factory = session_factory
        self._session: Session | None = None
        self._transaction: SessionTransaction | None = None

    @property
    def session(self) -> Session:
        if self._session is None:
            raise RuntimeError("UnitOfWork has not been entered")
        return self._session

    def __enter__(self) -> "UnitOfWork":
        if self._session is not None:
            raise RuntimeError("UnitOfWork cannot be entered more than once")
        self._session = self._session_factory()
        self._transaction = self._session.begin()
        return self

    def commit(self) -> None:
        """Commit every mutation in this local transaction."""

        if self._transaction is None or not self._transaction.is_active:
            raise RuntimeError("UnitOfWork has no active transaction")
        self._transaction.commit()

    def rollback(self) -> None:
        """Roll back every uncommitted mutation in this local transaction."""

        if self._transaction is not None and self._transaction.is_active:
            self._transaction.rollback()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            if self._transaction is not None and self._transaction.is_active:
                self._transaction.rollback()
        finally:
            if self._session is not None:
                self._session.close()
