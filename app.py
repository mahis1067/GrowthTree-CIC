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


def add_service_to_tree(tree, service_name):
    all_services = set(tree["year1"] + tree["year2"] + tree["year3"])
    if service_name in all_services:
        return tree

    year_targets = ["year1", "year2", "year3"]
    target_year = min(year_targets, key=lambda y: len(tree[y]))
    tree[target_year].append(service_name)
    return tree


def merge_purchased_into_tree(tree, purchased):
    for service_name in purchased:
        tree = add_service_to_tree(tree, service_name)
    return tree


def generate_growth_tree(answers):
    tree = default_tree()
    org_type = answers.get("organization_type")
    primary_reason = answers.get("primary_reason")
    journey_stage = answers.get("journey_stage")
    year1_benefit = answers.get("year1_benefit")
    governance_interest = answers.get("governance_interest")
    year2_goal = answers.get("year2_goal")

    if org_type in {"Municipality", "Business (small / medium / large)", "Public institution (school, hospital)"}:
        tree["year1"].extend(["Access Information", "Stay Informed"])
    elif org_type == "Nonprofit or association":
        tree["year1"].extend(["Networking Forum", "Multi-Sectoral Perspectives"])
    else:
        tree["year1"].extend(["Reduced Rates", "Stay Informed"])

    if primary_reason == "Influence policy and strategy" or governance_interest == "Yes: policy input/strategy":
        tree["year2"].append("Influence")
    elif primary_reason == "Connect with policymakers and peers":
        tree["year2"].append("Networking Forum")
    elif primary_reason == "Participate in committees or governance" or governance_interest == "Yes: committee work":
        tree["year2"].append("Multi-Sectoral Perspectives")
    else:
        tree["year2"].append("Access Information")

    if year2_goal == "Influence circular economy policy" or journey_stage in {"Leading initiatives", "Want to shape sector strategy"}:
        tree["year3"].append("Voting Privileges")
    else:
        tree["year3"].append("Reduced Rates")

    if year1_benefit == "Attending forums and workshops":
        tree["year1"].append("Reduced Rates")
    elif year1_benefit == "Serving on committees or advisory groups":
        tree["year2"].append("Influence")

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
        stage_to_years = {
            "Just getting started": "0",
            "Implementing projects": "1",
            "Leading initiatives": "2",
            "Want to shape sector strategy": "3",
            "Other": "0",
        }
        session["membership_years"] = stage_to_years.get(answers.get("journey_stage"), "0")
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
    if service_name not in tree_data["year1"] + tree_data["year2"] + tree_data["year3"]:
        tree_data = add_service_to_tree(tree_data, service_name)
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
