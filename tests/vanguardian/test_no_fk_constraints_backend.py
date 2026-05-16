from django.test import SimpleTestCase, override_settings

from Vanguardian.db.backends.mysql_no_constraints.schema import NoForeignKeyConstraintSchemaEditor


class NoForeignKeyConstraintSchemaEditorTests(SimpleTestCase):
    def _editor(self):
        return object.__new__(NoForeignKeyConstraintSchemaEditor)

    @override_settings(DATABASE_DISABLE_FOREIGN_KEY_CONSTRAINTS=True)
    def test_skips_foreign_key_sql_when_disabled(self):
        editor = self._editor()

        self.assertTrue(
            editor._should_skip_foreign_key_sql(
                "ALTER TABLE child ADD CONSTRAINT child_parent_fk FOREIGN KEY (parent_id) REFERENCES parent (id)"
            )
        )

    @override_settings(DATABASE_DISABLE_FOREIGN_KEY_CONSTRAINTS=True)
    def test_keeps_index_sql_when_foreign_key_constraints_are_disabled(self):
        editor = self._editor()

        self.assertFalse(editor._should_skip_foreign_key_sql("CREATE INDEX child_parent_idx ON child (parent_id)"))
        self.assertFalse(editor._should_skip_foreign_key_sql("CREATE UNIQUE INDEX child_code_uq ON child (code)"))

    @override_settings(DATABASE_DISABLE_FOREIGN_KEY_CONSTRAINTS=False)
    def test_keeps_foreign_key_sql_when_disabled_flag_is_off(self):
        editor = self._editor()

        self.assertFalse(
            editor._should_skip_foreign_key_sql(
                "ALTER TABLE child ADD CONSTRAINT child_parent_fk FOREIGN KEY (parent_id) REFERENCES parent (id)"
            )
        )
