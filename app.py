import os
import time
import MySQLdb
from flask import Flask, render_template, request, jsonify
from flask_mysqldb import MySQL

app = Flask(__name__)

# Correct defaults for Docker Compose
app.config["MYSQL_HOST"] = os.environ.get("MYSQL_HOST", "mysql")
app.config["MYSQL_USER"] = os.environ.get("MYSQL_USER", "root")
app.config["MYSQL_PASSWORD"] = os.environ.get("MYSQL_PASSWORD", "root")
app.config["MYSQL_DB"] = os.environ.get("MYSQL_DB", "devops")

mysql = MySQL(app)


def init_db(retries: int = 30, delay: int = 3) -> None:
    """
    Wait until MySQL is reachable, then initialize the schema.
    Handles cases where mysql.connection is None during startup.
    """
    with app.app_context():
        last_err = None
        while retries > 0:
            try:
                conn = mysql.connection
                if conn is None:
                    raise MySQLdb.OperationalError("mysql.connection is None (DB not ready yet)")

                cur = conn.cursor()
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS messages (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        message TEXT
                    )
                    """
                )
                conn.commit()
                cur.close()
                print("Database initialized successfully")
                return

            except Exception as e:
                last_err = e
                retries -= 1
                print(f"MySQL not ready ({e}); retrying in {delay}s... ({retries} left)")
                time.sleep(delay)

        raise RuntimeError(f"Database not available after retries. Last error: {last_err}")


@app.route("/")
def hello():
    cur = mysql.connection.cursor()
    cur.execute("SELECT message FROM messages")
    messages = cur.fetchall()
    cur.close()
    return render_template("index.html", messages=messages)


@app.route("/submit", methods=["POST"])
def submit():
    new_message = request.form.get("new_message", "")
    cur = mysql.connection.cursor()
    cur.execute("INSERT INTO messages (message) VALUES (%s)", (new_message,))
    mysql.connection.commit()
    cur.close()
    return jsonify({"message": new_message})


@app.route("/health")
def health():
    # DB-aware healthcheck (useful for docker/compose)
    try:
        cur = mysql.connection.cursor()
        cur.execute("SELECT 1")
        cur.close()
        return "ok", 200
    except Exception as e:
        return f"db not ready: {e}", 503


if __name__ == "__main__":
    init_db()
    # Do NOT enable debug reloader in Docker
    app.run(host="0.0.0.0", port=5000, debug=False)
