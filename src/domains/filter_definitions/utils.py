from src.domains.filter_definitions.enums import FilterType
from src.domains.filter_definitions.exceptions import InvalidCustomFiltersError
from src.domains.filter_definitions.models import FilterDefinition


def validate_select_options(options: dict | None) -> None:
    """Raises ValueError if options.values is missing or not a non-empty list."""
    values = (options or {}).get("values")
    if not values or not isinstance(values, list):
        raise ValueError(
            "options.values must be a non-empty list for SELECT filter type"
        )


def _validate_filter_value(
    slug: str, value: object, definition: FilterDefinition
) -> None:
    # Validates a single filter value against its definition's type rules.
    # Raises InvalidCustomFiltersError if the value doesn't match the expected type,
    # is not in the allowed options (SELECT), or is outside the min/max bounds (RANGE).
    # Note: bool is explicitly excluded from NUMBER/RANGE checks because in Python
    # bool is a subclass of int, so isinstance(True, int) is True
    match definition.filter_type:
        case FilterType.TEXT:
            if not isinstance(value, str):
                raise InvalidCustomFiltersError(f"Filter '{slug}' must be a string")
        case FilterType.NUMBER:
            if not isinstance(value, int | float) or isinstance(value, bool):
                raise InvalidCustomFiltersError(f"Filter '{slug}' must be a number")
        case FilterType.BOOLEAN:
            if not isinstance(value, bool):
                raise InvalidCustomFiltersError(f"Filter '{slug}' must be a boolean")
        case FilterType.SELECT:
            options: list = (definition.options or {}).get("values", [])
            if value not in options:
                raise InvalidCustomFiltersError(
                    f"Filter '{slug}' must be one of: {', '.join(str(o) for o in options)}"
                )
        case FilterType.RANGE:
            if not isinstance(value, int | float) or isinstance(value, bool):
                raise InvalidCustomFiltersError(f"Filter '{slug}' must be a number")

            bounds: dict = definition.options or {}
            if "min" in bounds and value < bounds["min"]:
                raise InvalidCustomFiltersError(
                    f"Filter '{slug}' must be >= {bounds['min']}"
                )
            if "max" in bounds and value > bounds["max"]:
                raise InvalidCustomFiltersError(
                    f"Filter '{slug}' must be <= {bounds['max']}"
                )
