"""
ORM package root: import subpackages so models register on ``Base.metadata``.

Alembic's ``env.py`` does ``import app.models``; this must load concrete model
modules or autogenerate sees an empty schema and emits only ``pass``.
"""

import app.models.auth  # noqa: F401
import app.models.simulation  # noqa: F401
