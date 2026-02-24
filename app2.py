from flask import Flask, render_template
import json
from datetime import datetime
app = Flask(__name__)


@app.route("/")
def home():
    return render_template("home.html")



app.run(debug=True)