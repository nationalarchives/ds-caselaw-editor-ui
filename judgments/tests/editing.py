from contextlib import contextmanager


def editing_order() -> list[str]:
    return []


def tracking_editing_session(order: list[str]):
    """Stand-in for ``Document.editing_session`` that records when the view enters and leaves it.

    The document mock does not take a real edit lock. The test checks that the
    persisted writes happen inside this context, which is the call the view owns.
    """

    @contextmanager
    def editing_session():
        order.append("editing_session")
        yield
        order.append("editing_session_end")

    return editing_session


def record(order: list[str], event: str, result=None):
    def side_effect(*args, **kwargs):
        order.append(event)
        return result

    return side_effect
