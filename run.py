# -*- encoding: utf-8 -*-


from api import app, db, mail


@app.shell_context_processor
def make_shell_context():
    return {
        "app": app,
        "db": db,
        "mail": mail,
    }


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
