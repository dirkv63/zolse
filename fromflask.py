import os
import platform
from competition import create_app, lm


# Run Application
app = create_app(os.getenv("FLASK_CONFIG"))


@app.shell_context_processor
def make_shell_context():
    return dict(app=app, lm=lm)
