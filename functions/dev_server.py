"""Local development server."""

from functions_framework import create_app

from src.api import app as flask_app

app = create_app(target="src.api:app", source=".")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5001, debug=True)
