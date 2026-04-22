"""Shared password validation bounds (stored hashes are fixed-size)."""

PASSWORD_MIN_LENGTH = 8
# Generous limit for password managers; request body size is the real bound.
PASSWORD_MAX_LENGTH = 4096
