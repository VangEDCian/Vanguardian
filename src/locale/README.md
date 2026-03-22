# Translation Organization

The translation catalogs are grouped by `module -> template/file` inside:

- `src/locale/en/LC_MESSAGES/django.po`
- `src/locale/vi/LC_MESSAGES/django.po`

Editing convention:

1. Source language is English: keep `msgid` in English.
2. Find the module block first (`Core Settings`, `Shared Layout`, `Dashboard`, `Identity`).
3. Inside that block, find the exact template/file section.
4. Update only `msgstr` for target language (for `vi`, write Vietnamese), keep `msgid` unchanged.

After editing `.po` files, rebuild `.mo` files so Django can load updates in runtime.
