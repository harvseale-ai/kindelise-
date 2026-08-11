#!/usr/bin/env python
"""Provide Django's standard management-command entry point."""

# KEYWORD: command line — the words typed after Python to choose a task, such as runserver or test.
# It does not contain the website’s main features; it provides the entry point for managing and running them.

import os
import sys


# WHY: Starts Django's chosen command when this file is run from the command line.
def main():
    """Run the requested Django management command."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
