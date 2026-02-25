import json
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for


app = Flask(__name__)
app.secret_key = "cic-growth-tree-dev"


DATA_PATH = Path(__file__).with_name("info.json")


def load_services():
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


SERVICES = load_services()
SERVICES_BY_TITLE = {service["title"]: service for service in SERVICES}


def default_tree():
    return {"year1": [], "year2": [], "year3": []}


def merge_purchased_into_tree(tree, purchased):
    all_services = set(tree["year1"] + tree["year2"] + tree["year3"])
    for service_name in purchased:
        if service_name not in all_services:
            tree["year1"].append(service_name)
            all_services.add(service_name)
    return tree


def generate_growth_tree(answers):
    tree = default_tree()
    org = answers.get("organization")
    goal = answers.get("goal")
    scale = answers.get("revenue")

    if org in {"Business", "Municipality/Government"}:
        tree["year1"].extend(["Access Information", "Stay Informed"])
    elif org == "Public Institution":
        tree["year1"].extend(["Access Information", "Multi-Sectoral Perspectives"])
    elif org == "Association/Non-Profit":
        tree["year1"].extend(["Networking Forum", "Multi-Sectoral Perspectives"])
    else:
        tree["year1"].extend(["Reduced Rates", "Stay Informed"])

    if goal == "Influence policy":
        tree["year2"].append("Influence")
    elif goal == "Build network":
        tree["year2"].append("Networking Forum")
    else:
        tree["year2"].append("Access Information")

    if scale in {"$500k-$2M", "$2M+"}:
        tree["year3"].append("Voting Privileges")
    else:
        tree["year3"].append("Reduced Rates")

    for year in tree:
        tree[year] = list(dict.fromkeys(tree[year]))

    purchased = session.get("purchased", [])
    return merge_purchased_into_tree(tree, purchased)


def calculate_tier():
    years_with_cic = int(session.get("membership_years", 0))
    purchased_count = len(session.get("purchased", []))

    if years_with_cic >= 3 or purchased_count >= 6:
        return "Gold"
    if years_with_cic >= 2 or purchased_count >= 3:
        return "Silver"
    if years_with_cic >= 1 or purchased_count >= 1:
        return "Bronze"
    return "New Member"


def tier_progress_percent():
    tier = calculate_tier()
    return {"New Member": 10, "Bronze": 35, "Silver": 68, "Gold": 100}[tier]


def purchased_details():
    purchased = session.get("purchased", [])
    details = [SERVICES_BY_TITLE[name] for name in purchased if name in SERVICES_BY_TITLE]
    return details


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if request.method == "POST":
        answers = request.form.to_dict()
        session["quiz_answers"] = answers
        session["membership_years"] = answers.get("years_with_cic", "0")
        session["growth_tree"] = generate_growth_tree(answers)

        new_tier = calculate_tier()
        previous = session.get("tier")
        session["tier"] = new_tier
        if previous and previous != new_tier:
            session["celebration"] = f"Congratulations! You advanced from {previous} to {new_tier} tier."

        return redirect(url_for("tree"))

    return render_template("quiz.html", answers=session.get("quiz_answers", {}))


@app.route("/tree")
def tree():
    tree_data = session.get("growth_tree", default_tree())
    tree_data = merge_purchased_into_tree(tree_data, session.get("purchased", []))
    session["growth_tree"] = tree_data

    celebration = session.pop("celebration", None)
    return render_template(
        "tree.html",
        tree=tree_data,
        tier=calculate_tier(),
        progress=tier_progress_percent(),
        services_map=SERVICES_BY_TITLE,
        celebration=celebration,
    )


@app.route("/services")
def services():
    purchased = set(session.get("purchased", []))
    return render_template("services.html", services=SERVICES, purchased=purchased)


@app.route("/buy/<service_name>")
def buy(service_name):
    if service_name not in SERVICES_BY_TITLE:
        return redirect(url_for("services"))

    purchased = session.get("purchased", [])
    if service_name not in purchased:
        purchased.append(service_name)
    session["purchased"] = purchased

    tree_data = session.get("growth_tree", default_tree())
    session["growth_tree"] = merge_purchased_into_tree(tree_data, purchased)

    old_tier = session.get("tier")
    new_tier = calculate_tier()
    session["tier"] = new_tier
    if old_tier and old_tier != new_tier:
        session["celebration"] = f"Great work! You reached {new_tier} tier."

    return redirect(request.args.get("next") or url_for("tree"))


@app.route("/tier")
def tier():
    return render_template(
        "tier.html",
        tier=calculate_tier(),
        progress=tier_progress_percent(),
        purchased_count=len(session.get("purchased", [])),
        years_with_cic=session.get("membership_years", "0"),
    )


@app.route("/invoice")
def invoice():
    items = purchased_details()
    total = sum(item["price"] for item in items)
    return render_template("invoice.html", items=items, total=total)


if __name__ == "__main__":
    app.run(debug=True)
