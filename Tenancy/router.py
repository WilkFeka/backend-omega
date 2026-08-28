from Tenancy.context import get_tenant_db


TENANT_APPS = {
    "Employees",
    "Salaries",
    "Loans",
    "VatRefunds",
    "Expenses",
}


class TenantDatabaseRouter:

    def db_for_read(
        self,
        model,
        **hints
    ):

        if model._meta.app_label in TENANT_APPS:
            return get_tenant_db()

        return "default"

    def db_for_write(
        self,
        model,
        **hints
    ):

        if model._meta.app_label in TENANT_APPS:
            return get_tenant_db()

        return "default"

    def allow_relation(
        self,
        obj1,
        obj2,
        **hints
    ):

        db1 = getattr(
            obj1._state,
            "db",
            None
        )

        db2 = getattr(
            obj2._state,
            "db",
            None
        )

        if db1 and db2:
            return db1 == db2

        return None

    def allow_migrate(
        self,
        db,
        app_label,
        model_name=None,
        **hints
    ):

        if app_label in TENANT_APPS:
            return db != "default"

        return db == "default"
