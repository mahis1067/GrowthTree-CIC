from flask import Flask, jsonify, redirect, render_template, request, url_for, session


app = Flask(__name__)



@app.route ('/', methods=["GET", "POST"])
def index():
    if request.method == "POST":
        prompt = request.form.get("prompt")
        print (prompt)
        return render_template("index.html")
    else:
        return render_template("index.html")


@app.route('/home')
def home():
    name = session.get('name', 'Guest')  
    return render_template('home.html', name=name)

@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if request.method == "POST":
        answers = request.form
        session["quiz_answers"] = answers
        generate_growth_tree(answers)
        return redirect(url_for("tree"))

    return render_template("quiz.html")

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