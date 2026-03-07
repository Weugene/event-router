import uuid
from contextvars import ContextVar


trace_id_ctx_var: ContextVar[str] = ContextVar("trace_id", default="-")


def set_trace_id(trace_id: str | None = None) -> str:
    value = trace_id or str(uuid.uuid4())
    trace_id_ctx_var.set(value)
    return value


def get_trace_id() -> str:
    return trace_id_ctx_var.get()
