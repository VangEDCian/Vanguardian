from django.db.backends.mysql.base import DatabaseWrapper as MySQLDatabaseWrapper

from .schema import NoForeignKeyConstraintSchemaEditor


class DatabaseWrapper(MySQLDatabaseWrapper):
    SchemaEditorClass = NoForeignKeyConstraintSchemaEditor
