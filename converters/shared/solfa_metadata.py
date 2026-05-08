"""Default solfa metadata headers for converters."""

from .solfa_spec import spec

# Build default headers template from spec
DEFAULT_HEADERS = []

# Add all header properties in order
prefix = spec["header"]["prop_prefix"]
suffix = spec["header"]["prop_suffix"]

for prop_key, default_val in spec["defaults"].items():
    header_line = f"{prefix}{prop_key}{suffix} {default_val}"
    DEFAULT_HEADERS.append(header_line)

# Also available as a formatted string for easy insertion
DEFAULT_HEADERS_TEXT = "\n".join(DEFAULT_HEADERS) + "\n"
