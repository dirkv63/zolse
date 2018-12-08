import platform
from competition import create_app
from waitress import serve


# Run Application
if __name__ == "__main__":
    env = "development"
    if platform.node() == "zeegeus":
        env = "production"
    app = create_app(env)

    if env == "development":
        app.run()
    else:
        serve(app, listen='127.0.0.1:18103')
