"""Package initializer for python_model_service.

Exports the Flask `app` at package level so tests and other code can do:

    from python_model_service import app as flask_app

This module deliberately performs a simple re-export and does not execute
application startup logic beyond what importing `app` entails.
"""

from .app import app  # re-export the Flask application

__all__ = ["app"]