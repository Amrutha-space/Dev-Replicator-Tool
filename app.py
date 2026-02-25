from flask import Flask, send_from_directory

app = Flask(__name__, static_folder="ui", static_url_path="")

@app.route("/")
def home():
    return send_from_directory("ui", "index.html")

if __name__ == "__main__":
    app.run(debug=True)