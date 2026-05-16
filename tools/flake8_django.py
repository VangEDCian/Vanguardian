import ast


class DjangoChecker:
    name = "flake8-django-local"
    version = "0.1.0"

    _index_name_max_length = 30

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename

    def run(self):
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Call):
                yield from self._check_index_name(node)

    def _check_index_name(self, node):
        if not _is_django_index_call(node):
            return

        name_keyword = next((keyword for keyword in node.keywords if keyword.arg == "name"), None)
        if name_keyword is None:
            return
        if not isinstance(name_keyword.value, ast.Constant) or not isinstance(name_keyword.value.value, str):
            return

        index_name = name_keyword.value.value
        if len(index_name) <= self._index_name_max_length:
            return

        yield (
            name_keyword.value.lineno,
            name_keyword.value.col_offset,
            (
                "DJG030 Django index name cannot be longer than "
                f"{self._index_name_max_length} characters "
                f"(got {len(index_name)}): {index_name!r}; "
                "Django system check models.E034 rejects longer names"
            ),
            type(self),
        )


def _is_django_index_call(node):
    if isinstance(node.func, ast.Attribute):
        return isinstance(node.func.value, ast.Name) and node.func.value.id == "models" and node.func.attr == "Index"
    return isinstance(node.func, ast.Name) and node.func.id == "Index"
