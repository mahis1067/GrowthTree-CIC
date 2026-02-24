from flask import Flask, render_template, request, redirect, url_for, session
import json
from datetime import datetime
import os

app = Flask(__name__, template_folder=os.path.join(os.path.dirname(__file__), 'template'), static_folder=os.path.join(os.path.dirname(__file__), 'static'))
app.secret_key = "cic_secret_key"

# Load service data
script_dir = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(script_dir, "info.json")) as f:
    SERVICES = json.load(f)


# -------------------------
# HOME
# -------------------------
@app.route("/")
def home():
    return render_template("home.html")


# -------------------------
# QUIZ
# -------------------------
@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if request.method == "POST":
        answers = request.form
        session["quiz_answers"] = answers
        generate_growth_tree(answers)
        return redirect(url_for("tree"))

    return render_template("quiz.html")


# -------------------------
# GROWTH TREE LOGIC
# -------------------------
def generate_growth_tree(answers):
    tree = {
        "year1": [],
        "year2": [],
        "year3": []
    }

    # Example Decision Logic
    if answers.get("organization") == "Business":
        tree["year1"].append("Research Access")
        tree["year1"].append("Networking Forum")

    if answers.get("involvement") == "Lead discussions":
        tree["year2"].append("Advisory Committee")

    if answers.get("goal") == "Influence circular economy policy":
        tree["year3"].append("Governance Voting Rights")

    session["growth_tree"] = tree


# -------------------------
# TREE PAGE
# -------------------------
@app.route("/tree")
def tree():
    tree = session.get("growth_tree", {})
    tier = calculate_tier()
    return render_template("tree.html", tree=tree, tier=tier)


# -------------------------
# SERVICES PAGE
# -------------------------
@app.route("/services")
def services():
    return render_template("services.html", services=SERVICES)


@app.route("/buy/<service_name>")
def buy(service_name):
    if "purchased" not in session:
        session["purchased"] = []

    session["purchased"].append(service_name)
    session.modified = True

    return redirect(url_for("tree"))


# -------------------------
# TIER SYSTEM
# -------------------------
def calculate_tier():
    purchased = session.get("purchased", [])
    years = len(purchased)

    if years >= 6:
        return "Gold"
    elif years >= 3:
        return "Silver"
    elif years >= 1:
        return "Bronze"
    else:
        return "New Member"


@app.route("/tier")
def tier():
    tier = calculate_tier()
    return render_template("tier.html", tier=tier)


# -------------------------
# INVOICE
# -------------------------
@app.route("/invoice")
def invoice():
    purchased = session.get("purchased", [])
    total = 0

    for service in SERVICES:
        if service["title"] in purchased:
            total += service["price"]

    return render_template("invoice.html", purchased=purchased, total=total)


if __name__ == "__main__":
    app.run(debug=True)