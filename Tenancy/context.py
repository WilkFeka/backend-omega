from contextvars import ContextVar


_current_tenant_db = ContextVar(
    "current_tenant_db",
    default=None    
)


def set_tenant_db(alias):
    return _current_tenant_db.set(alias)


def reset_tenant_db(token):
    _current_tenant_db.reset(token)


def get_tenant_db():
    return _current_tenant_db.get()