import ast
from pathlib import Path


class DDDChecker:
    name = "flake8-ddd"
    version = "0.1.0"

    _layer_rank = {
        "presentation": 0,
        "application": 1,
        "domain": 2,
        "infrastructure": 3,
    }
    _allowed_forward_imports = {
        "presentation": {"presentation", "application"},
        "application": {"application", "domain", "infrastructure"},
        "domain": {"domain", "infrastructure"},
        "infrastructure": {"infrastructure"},
        "public": {"application"},
    }
    _application_data_suffixes = ("Command", "Query")
    _presentation_data_suffixes = ("DTO", "Dto", "Form")
    _domain_data_suffixes = ("Entity",)
    _infrastructure_data_suffixes = ("Model",)

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename
        self.file_context = _FileContext.from_filename(filename)

    def run(self):
        if not self.file_context.is_app_file:
            return

        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                yield from self._check_import(node)
            elif isinstance(node, ast.ImportFrom):
                yield from self._check_import_from(node)

    def _check_import(self, node):
        for alias in node.names:
            yield from self._check_import_target(
                module_name=alias.name,
                imported_name=alias.asname or alias.name.rsplit(".", 1)[-1],
                lineno=node.lineno,
                col=node.col_offset,
            )

    def _check_import_from(self, node):
        module_name = self._resolve_import_from_module(node)
        if not module_name:
            return

        for alias in node.names:
            imported_name = alias.asname or alias.name
            target_module = module_name
            if alias.name != "*":
                target_module = f"{module_name}.{alias.name}"
            yield from self._check_import_target(
                module_name=target_module,
                imported_name=imported_name,
                lineno=node.lineno,
                col=node.col_offset,
            )

    def _resolve_import_from_module(self, node):
        if node.level <= 0:
            return node.module

        base_parts = self.file_context.module_path_parts[:-1]
        if node.level > 1:
            base_parts = base_parts[: -(node.level - 1)]

        if node.module:
            base_parts = [*base_parts, *node.module.split(".")]
        return ".".join(base_parts)

    def _check_import_target(self, *, module_name, imported_name, lineno, col):
        target = _ImportTarget.from_module_name(module_name)
        if target is None:
            return

        if target.app_name != self.file_context.app_name:
            return

        yield from self._check_same_app_layer_import(target=target, lineno=lineno, col=col)
        yield from self._check_layer_entity_usage(
            target=target,
            imported_name=imported_name,
            lineno=lineno,
            col=col,
        )
        yield from self._check_mapper_boundary(
            target=target,
            imported_name=imported_name,
            lineno=lineno,
            col=col,
        )

    def _check_same_app_layer_import(self, *, target, lineno, col):
        source_layer = self.file_context.layer
        target_layer = target.layer
        if source_layer is None or target_layer is None:
            return

        allowed_layers = self._allowed_forward_imports.get(source_layer, {source_layer})
        if target_layer not in allowed_layers:
            yield (
                lineno,
                col,
                (
                    "DDD001 invalid same-app layer import: "
                    f"{source_layer} must not import {target_layer}; "
                    "allowed flow is public/presentation -> application -> domain/infrastructure"
                ),
                type(self),
            )

    def _check_layer_entity_usage(self, *, target, imported_name, lineno, col):
        source_layer = self.file_context.layer
        if source_layer is None or self.file_context.is_mapper:
            return

        if source_layer == "presentation" and _endswith_any(imported_name, self._domain_data_suffixes):
            yield (
                lineno,
                col,
                "DDD010 presentation must use DTO/Form objects, not domain entities directly",
                type(self),
            )

        if source_layer == "presentation" and _endswith_any(imported_name, self._infrastructure_data_suffixes):
            yield (
                lineno,
                col,
                "DDD011 presentation must use DTO/Form objects, not infrastructure models directly",
                type(self),
            )

        if source_layer == "application" and _endswith_any(imported_name, self._presentation_data_suffixes):
            yield (
                lineno,
                col,
                "DDD012 application must use Command/Query objects, not presentation DTO/Form objects",
                type(self),
            )

        if source_layer == "domain" and target.is_django_model_import:
            yield (
                lineno,
                col,
                "DDD013 domain must use entities; Django models belong to infrastructure mappers",
                type(self),
            )

    def _check_mapper_boundary(self, *, target, imported_name, lineno, col):
        source_layer = self.file_context.layer
        if source_layer is None or self.file_context.is_mapper:
            return

        if source_layer == "presentation" and target.layer == "application":
            if _endswith_any(imported_name, self._application_data_suffixes):
                yield (
                    lineno,
                    col,
                    "DDD020 map DTO/Form to Command/Query in a presentation mapper",
                    type(self),
                )

        if source_layer == "application" and target.layer == "domain":
            if _endswith_any(imported_name, self._domain_data_suffixes):
                yield (
                    lineno,
                    col,
                    "DDD021 map Command/Query to Entity in an application mapper",
                    type(self),
                )

        if source_layer == "application" and target.layer == "infrastructure":
            if target.is_django_model_import or _endswith_any(imported_name, self._infrastructure_data_suffixes):
                yield (
                    lineno,
                    col,
                    "DDD022 map Command/Query to Django Model in an application mapper",
                    type(self),
                )

        if source_layer == "domain" and target.layer == "infrastructure":
            if target.is_django_model_import or _endswith_any(imported_name, self._infrastructure_data_suffixes):
                yield (
                    lineno,
                    col,
                    "DDD023 map Entity to Django Model in a domain mapper",
                    type(self),
                )

class _FileContext:
    def __init__(self, *, app_name, layer, module_path_parts, is_app_file, is_mapper):
        self.app_name = app_name
        self.layer = layer
        self.module_path_parts = module_path_parts
        self.is_app_file = is_app_file
        self.is_mapper = is_mapper

    @classmethod
    def from_filename(cls, filename):
        path = Path(filename)
        parts = path.parts
        apps_index = _find_apps_index(parts)
        if apps_index is None or len(parts) <= apps_index + 1:
            return cls(app_name=None, layer=None, module_path_parts=[], is_app_file=False, is_mapper=False)

        app_name = parts[apps_index + 1]
        relative_parts = list(parts[apps_index + 2 :])
        module_path_parts = ["apps", app_name, *_strip_py_suffix(relative_parts)]
        layer = _layer_from_relative_parts(relative_parts)
        is_mapper = _is_mapper_path(relative_parts)
        return cls(
            app_name=app_name,
            layer=layer,
            module_path_parts=module_path_parts,
            is_app_file=True,
            is_mapper=is_mapper,
        )


class _ImportTarget:
    def __init__(self, *, app_name, layer, is_django_model_import):
        self.app_name = app_name
        self.layer = layer
        self.is_django_model_import = is_django_model_import

    @classmethod
    def from_module_name(cls, module_name):
        if not module_name:
            return None
        parts = module_name.split(".")
        if len(parts) < 2 or parts[0] != "apps":
            return None

        app_name = parts[1]
        relative_parts = parts[2:]
        return cls(
            app_name=app_name,
            layer=_layer_from_relative_parts(relative_parts),
            is_django_model_import=_is_model_import(relative_parts),
        )


def _find_apps_index(parts):
    for index, part in enumerate(parts):
        if part == "apps":
            return index
    return None


def _layer_from_relative_parts(relative_parts):
    if not relative_parts:
        return None
    first = relative_parts[0]
    if first == "public.py" or first == "public":
        return "public"
    if first == "models.py" or first == "models":
        return "infrastructure"
    if first in DDDChecker._layer_rank:
        return first
    return None


def _strip_py_suffix(parts):
    stripped_parts = []
    for part in parts:
        if part.endswith(".py"):
            stripped_parts.append(part[:-3])
        else:
            stripped_parts.append(part)
    return stripped_parts


def _is_mapper_path(relative_parts):
    return any(part in {"mapper", "mappers", "mapping", "adapters"} for part in relative_parts) or any(
        "mapper" in part or "mapping" in part for part in relative_parts
    )


def _is_model_import(relative_parts):
    if not relative_parts:
        return False
    return relative_parts[0] in {"models", "models.py"} or relative_parts[-1] in {"models", "models.py"}


def _endswith_any(value, suffixes):
    return any((value or "").endswith(suffix) for suffix in suffixes)
