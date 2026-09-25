"""Manifest-driven config form MODEL — the schema half of every kit form.

Auto-generates a capability config UI's model from a manifest's
`config_schema.properties` (the pydantic-emitted JSON Schema every substrate
capability already ships): field order, titles, kinds, enum options, bounds,
defaults. The ratified interaction shape is a ROW PER FIELD painted by the
consumer (a FormShell body, a stacked config page) with closed sets
(enums/bools) cycled in place and a TRANSIENT editor as the typed-value
escape hatch — this module owns the semantics (cycle, parse/validate,
diff-from-default), the consuming surface owns the widgets. `overrides()`
yields exactly the non-default config dict the load-directive/spec grammar
wants (`spec_string`'s config operand), so a form edit round-trips to a
reproducible headless invocation.

Born as the tui-kit's form module (work item aafce2c6, drive 1 2026-07-15;
demand: the voxtral-small device=cpu case had no in-TUI expression) and
ported here unchanged in semantics by the Textual retirement (ruling
8b7351e4, work item 21145648): the model was pure Python from birth, and
the three Qt apps that import it are its only consumers.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ConfigField:
    """One schema property as an editable form row.

    Closed sets (enum options, bools) cycle in place; everything else takes
    typed text through `parse` (the transient-editor escape hatch). `modified`
    is the diff-from-default flag the row paints and `overrides()` filters on.
    """
    key: str                        # Property name (the config dict key)
    kind: str                       # 'bool' | 'integer' | 'number' | 'string'
    default: Any = None             # Schema default (None = absent or null)
    value: Any = None               # Current value (starts at the default)
    title: str = ""                 # Display label (schema title, else the key)
    description: str = ""           # One-line help (schema description)
    options: List[Any] = field(default_factory=list)  # Closed set (enum); [] = open
    nullable: bool = False          # 'null' in the schema's type union
    minimum: Optional[float] = None  # Numeric lower bound (inclusive)
    maximum: Optional[float] = None  # Numeric upper bound (inclusive)

    @property
    def modified(self) -> bool:  # True = differs from the schema default
        return self.value != self.default

    def cycle(self, delta: int = 1) -> bool:
        """Step a closed set in place (enum options + none when nullable, or a
        bool toggle). Returns False for open kinds — the caller falls back to
        the transient editor."""
        if self.kind == "bool":
            self.value = not bool(self.value)
            return True
        if self.options:
            ring = list(self.options) + ([None] if self.nullable else [])
            i = ring.index(self.value) if self.value in ring else -delta
            self.value = ring[(i + delta) % len(ring)]
            return True
        return False

    def parse(self, text: str) -> Any:
        """Coerce transient-editor text to this field's type, assign and return it.

        Raises ValueError with a row-paintable reason (bad literal, out of
        bounds, not an option) and leaves the value untouched on failure."""
        t = text.strip()
        if self.nullable and t.lower() in ("", "none", "null"):
            self.value = None
            return None
        if self.kind == "bool":
            if t.lower() not in ("true", "false"):
                raise ValueError("expected true or false")
            value: Any = (t.lower() == "true")
        elif self.kind in ("integer", "number"):
            try:
                value = int(t) if self.kind == "integer" else float(t)
            except ValueError:
                raise ValueError(f"expected a{'n integer' if self.kind == 'integer' else ' number'}")
            if self.minimum is not None and value < self.minimum:
                raise ValueError(f"minimum is {self.minimum}")
            if self.maximum is not None and value > self.maximum:
                raise ValueError(f"maximum is {self.maximum}")
        elif self.options:
            by_render = {str(o): o for o in self.options}
            if t not in by_render:
                raise ValueError("not one of: " + ", ".join(str(o) for o in self.options))
            value = by_render[t]
        else:
            value = t
        self.value = value
        return value

    def render(self) -> str:
        """Row-paintable value string (spec-grammar shapes: lowercase bools,
        'none' for null — what `parse` round-trips)."""
        if self.value is None:
            return "none"
        if isinstance(self.value, bool):
            return "true" if self.value else "false"
        return str(self.value)


class ConfigForm:
    """A capability's editable config, derived from its manifest config_schema.

    The form is the MODEL half of the ratified shape (row-per-field +
    transient-editor escape hatch): `rows()` feeds the consumer's row paint,
    `apply()` adopts persisted or spec overrides, and `overrides()` yields the
    non-default config dict a load directive / spec string carries. Field
    order is the schema's property order.
    """

    def __init__(
        self,
        fields: List[ConfigField],  # The form's rows, in display order
    ):
        self.fields = fields

    @classmethod
    def from_schema(
        cls,
        config_schema: Optional[Dict[str, Any]],  # A manifest's config_schema section
        skip: Tuple[str, ...] = (),               # Property keys another view owns (the model axis)
    ) -> "ConfigForm":
        """Build a form from `config_schema.properties` (order preserved).

        `skip` drops axes with a specialized view — the model picker owns the
        model axis, so the form shows everything else."""
        props = (config_schema or {}).get("properties") or {}
        fields: List[ConfigField] = []
        for key, schema in props.items():
            if key in skip or not isinstance(schema, dict):
                continue
            types = schema.get("type")
            types = types if isinstance(types, list) else [types]
            base = next((t for t in types if t and t != "null"), "string")
            kind = {"boolean": "bool", "integer": "integer",
                    "number": "number"}.get(base, "string")
            fields.append(ConfigField(
                key=key, kind=kind,
                default=schema.get("default"), value=schema.get("default"),
                title=schema.get("title") or key,
                description=schema.get("description") or "",
                options=list(schema.get("enum") or []),
                nullable="null" in types,
                minimum=schema.get("minimum"), maximum=schema.get("maximum")))
        return cls(fields)

    def field(
        self,
        key: str,  # A property key
    ) -> ConfigField:  # Its form field (KeyError when the schema has no such row)
        """Look a field up by config key."""
        for f in self.fields:
            if f.key == key:
                return f
        raise KeyError(key)

    def apply(
        self,
        config: Dict[str, Any],  # Persisted/spec overrides to adopt
    ) -> None:
        """Adopt existing overrides (unknown keys ignored — stale persisted
        state must never break the form)."""
        for f in self.fields:
            if f.key in config:
                f.value = config[f.key]

    def overrides(self) -> Dict[str, Any]:  # Non-default values, schema order
        """The form's diff from defaults — exactly a load directive's config
        operand (empty dict = the capability's default instance)."""
        return {f.key: f.value for f in self.fields if f.modified}

    def rows(self) -> List[Tuple[str, str, bool]]:  # (title, value, modified) per field
        """Row data for the consumer's row paint (one line per field)."""
        return [(f.title, f.render(), f.modified) for f in self.fields]
