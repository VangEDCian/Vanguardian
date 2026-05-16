from django.conf import settings
from django.db.backends.mysql.schema import DatabaseSchemaEditor as MySQLDatabaseSchemaEditor


class NoForeignKeyConstraintSchemaEditor(MySQLDatabaseSchemaEditor):
    """MySQL schema editor that keeps FK fields but skips FK DDL in production."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._foreign_key_constraints_disabled():
            # MySQL can inline FK DDL in ADD COLUMN. Force it to deferred SQL so
            # execute() can skip only the FK statement without skipping the column.
            self.sql_create_column_inline_fk = None

    def execute(self, sql, params=()):
        if self._should_skip_foreign_key_sql(sql):
            return None
        return super().execute(sql, params=params)

    @staticmethod
    def _foreign_key_constraints_disabled():
        return bool(getattr(settings, "DATABASE_DISABLE_FOREIGN_KEY_CONSTRAINTS", False))

    def _should_skip_foreign_key_sql(self, sql):
        if sql is None or not self._foreign_key_constraints_disabled():
            return sql is None
        return "FOREIGN KEY" in str(sql).upper()
