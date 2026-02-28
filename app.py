import json
import secrets
from pathlib import Path

from flask import Flask, redirect, render_template, request, session, url_for


app = Flask(__name__)
app.secret_key = "cic-growth-tree-dev"
APP_RUN_ID = secrets.token_hex(8)


DATA_PATH = Path(__file__).with_name("info.json")
TIER_BUNDLE_PATH = Path(__file__).with_name("entities").joinpath("tier_bundles.json")
RULES_PATH = Path(__file__).with_name("entities").joinpath("recommendation_rules.json")


def load_services():
    # Open the JSON file and load its contents
    with DATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_tier_bundles():
    with TIER_BUNDLE_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_recommendation_rules():
    with RULES_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


SERVICES = load_services()  # Load all services from the JSON file
TIER_BUNDLES = load_tier_bundles()
RECOMMENDATION_RULES = load_recommendation_rules()
# Create a dictionary mapping service titles to their full data for quick lookup
SERVICES_BY_TITLE = {service["title"]: service for service in SERVICES}
TIER_ORDER = ["Bronze", "Silver", "Gold"]
YEAR_ORDER = ["year1", "year2", "year3"]
SERVICE_TIER_MAP = {
    service.get("title"): tier.get("name")
    for tier in TIER_BUNDLES.get("tiers", [])
    for service in tier.get("services", [])
}


def default_tree():
    # Create an empty growth tree with three years
    return {"year1": [], "year2": [], "year3": []}


def add_service_to_tree(tree, service_name):
    # Combine all services already in the tree into a set (to avoid duplicates)
    all_services = set(tree["year1"] + tree["year2"] + tree["year3"])
    # If the service is already in the tree, return unchanged
    if service_name in all_services:
        return tree

    # Define the year buckets
    year_targets = ["year1", "year2", "year3"]
    # Choose the year with the fewest services
    target_year = min(year_targets, key=lambda y: len(tree[y]))
    # Add the service to that year
    tree[target_year].append(service_name)
    return tree


def merge_purchased_into_tree(tree, purchased):
    # Ensure all purchased services are included in the tree
    for service_name in purchased:
        tree = add_service_to_tree(tree, service_name)
    return tree

def collect_recommended_services(answers, bundled_services):
    option_service_map = RECOMMENDATION_RULES.get("option_service_map", {})
    service_hits = {}

    bundled_titles = {service.get("title") for service in bundled_services}
    for field, field_map in option_service_map.items():
        answer = answers.get(field)
        if not answer:
            continue

        for service_title in field_map.get(answer, []):
            if service_title in bundled_titles:
                service_hits[service_title] = service_hits.get(service_title, 0) + 1

    return service_hits



def collect_recommended_subservices(answers, bundled_services):
    option_subservice_map = RECOMMENDATION_RULES.get("option_subservice_map", {})
    bundled_titles = {service.get("title") for service in bundled_services}
    collected = {}

    for field, field_map in option_subservice_map.items():
        answer = answers.get(field)
        if not answer:
            continue

        for item in field_map.get(answer, []):
            service_title = item.get("service")
            subservice = item.get("subservice")
            if not service_title or not subservice or service_title not in bundled_titles:
                continue

            entries = collected.setdefault(service_title, [])
            if subservice not in entries:
                entries.append(subservice)

    return collected

def accessible_tiers(current_tier):
    if current_tier not in TIER_ORDER:
        return ["Bronze"]
    return TIER_ORDER[: TIER_ORDER.index(current_tier) + 1]


def selected_bundle_tier():
    selected = session.get("selected_bundle")
    calculated = calculate_tier()

    if selected in TIER_ORDER and calculated in TIER_ORDER:
        return TIER_ORDER[max(TIER_ORDER.index(selected), TIER_ORDER.index(calculated))]
    if selected in TIER_ORDER:
        return selected
    if calculated in TIER_ORDER:
        return calculated
    return "Bronze"


def bundle_services_for_tier(current_tier):
    unlocked = set(accessible_tiers(current_tier))
    bundled = []
    for tier in TIER_BUNDLES.get("tiers", []):
        if tier.get("name") in unlocked:
            for service in tier.get("services", []):
                enriched = dict(service)
                enriched["tier"] = tier.get("name")
                bundled.append(enriched)
    return bundled


def all_bundle_services():
    bundled = []
    for tier in TIER_BUNDLES.get("tiers", []):
        for service in tier.get("services", []):
            enriched = dict(service)
            enriched["tier"] = tier.get("name")
            bundled.append(enriched)
    return bundled


def service_is_unlocked(service_name, current_tier):
    required_tier = SERVICE_TIER_MAP.get(service_name)
    if not required_tier:
        return True
    return required_tier in accessible_tiers(current_tier)


def generate_growth_tree(answers):
    # Start with an empty tree
    tree = default_tree()
    current_tier = selected_bundle_tier()
    bundled_services = all_bundle_services()
    service_hits = collect_recommended_services(answers, bundled_services)
    service_lookup = {service["title"]: service for service in bundled_services}
    tier_rank = {tier: index for index, tier in enumerate(TIER_ORDER)}
    year_rank = {year: index for index, year in enumerate(YEAR_ORDER)}

    # Sort matched services by tier, then by number of matching quiz options.
    sorted_matches = sorted(
        service_hits.items(),
        key=lambda item: (
            tier_rank.get(service_lookup[item[0]].get("tier"), 99),
            -item[1],
            year_rank.get(service_lookup[item[0]].get("preferred_year", "year2"), 1),
        ),
    )

    if not sorted_matches:
        sorted_matches = [(service.get("title"), 0) for service in bundled_services]

    for service_title, _ in sorted_matches:
        service = service_lookup.get(service_title)
        if not service:
            continue
        target_year = service.get("preferred_year", "year2")
        if target_year not in YEAR_ORDER:
            target_year = "year2"
        tree[target_year].append(service_title)

    # Add purchased services into the tree
    purchased = session.get("purchased", [])
    return merge_purchased_into_tree(tree, purchased)


def calculate_tier():
    # Get number of years and purchased services from session
    years_with_cic = int(session.get("membership_years", 0))
    purchased_count = len(session.get("purchased", []))

    #Determine tier based on years or purchases
    if years_with_cic >= 3 or purchased_count >= 6:
        return "Gold"
    if years_with_cic >= 2 or purchased_count >= 3:
        return "Silver"
    if years_with_cic >= 1 or purchased_count >= 1:
        return "Bronze"
    return "New Member"


def classify_bundle(org_type, journey_stage):
    # Classfy organization into a bundle category
    if org_type == "Public institution (school, hospital)":
        return "public"
    if org_type == "Municipality":
        return "municipality"
    if org_type in {"Business (small / medium / large)", "Nonprofit or association"}:
        if journey_stage in {"Leading initiatives", "Want to shape sector strategy"}:
            return "large_org"
        return "small_org"
    return "individual"


def tier_progress_percent():
    # Map tier to progress percentage
    tier = calculate_tier()
    return {"New Member": 10, "Bronze": 35, "Silver": 68, "Gold": 100}[tier]




def current_discount_percent():
    # Return discount based on tier
    tier = calculate_tier()
    if tier == "Gold":
        return 30
    if tier == "Silver":
        return 15
    return 0


def purchased_details():
    # Get detailed info for all purchased services
    purchased = session.get("purchased", [])
    details = [SERVICES_BY_TITLE[name] for name in purchased if name in SERVICES_BY_TITLE]
    return details




@app.before_request
def reset_session_on_new_server_run():
    # Ensure every new Flask run starts with a clean browser session state.
    if session.get("_app_run_id") != APP_RUN_ID:
        session.clear()
        session["_app_run_id"] = APP_RUN_ID


@app.route("/")
def index():
    # Render homepage
    return render_template("index.html")


@app.route("/quiz", methods=["GET", "POST"])
def quiz():
    if request.method == "POST":
        # Save user answers from form
        answers = request.form.to_dict()
        session["quiz_answers"] = answers
        # Keep membership/tier baseline from selected bundle so quiz answers
        # do not unlock higher tiers prematurely.
        if not session.get("selected_bundle") and "membership_years" not in session:
            stage_to_years = {
                "Just getting started": "0",
                "Implementing projects": "1",
                "Leading initiatives": "2",
                "Want to shape sector strategy": "3",
                "Other": "0",
            }
            session["membership_years"] = stage_to_years.get(answers.get("journey_stage"), "0")

        # Generate growth tree based on answers
        session["growth_tree"] = generate_growth_tree(answers)
        session["recommended_subservices"] = collect_recommended_subservices(
            answers,
            all_bundle_services(),
        )

        # Update tier and check if tier advanced
        new_tier = calculate_tier()
        previous = session.get("tier")
        session["tier"] = new_tier
        if previous and previous != new_tier:
            session["celebration"] = f"Congratulations! You advanced from {previous} to {new_tier} tier."

        return redirect(url_for("tree"))

    # Ask users to choose a bundle before the quiz
    if not session.get("selected_bundle"):
        return redirect(url_for("tier"))

    # Render quiz page with previous answers
    return render_template("quiz.html", answers=session.get("quiz_answers", {}), selected_bundle=session.get("selected_bundle"))


@app.route("/tree")
def tree():
    # Get current tree from session or create default
    tree_data = session.get("growth_tree", default_tree())
    # Ensure purchased services are included
    tree_data = merge_purchased_into_tree(tree_data, session.get("purchased", []))
    session["growth_tree"] = tree_data

    # Get and remove celebratory message
    celebration = session.pop("celebration", None)
    # Get added services
    purchased_names = session.get("purchased", [])

    # Render tree page with all relevant data
    current_tier = selected_bundle_tier()
    locked_services = {
        service_name
        for service_name in tree_data["year1"] + tree_data["year2"] + tree_data["year3"]
        if service_name not in purchased_names and not service_is_unlocked(service_name, current_tier)
    }
    return render_template(
        "tree.html",
        tree=tree_data,
        tier=current_tier,
        progress=tier_progress_percent(),
        services_map=SERVICES_BY_TITLE,
        purchased=set(purchased_names),
        purchased_count=len(purchased_names),
        unlocked_count=len(SERVICE_TIER_MAP) - len(locked_services),
        celebration=celebration,
        locked_services=locked_services,
        service_tier_map=SERVICE_TIER_MAP,
        recommended_subservices=session.get("recommended_subservices", {}),
    )


@app.route("/services")
def services():
    # Show all services and mark purchased ones
    purchased = set(session.get("purchased", []))
    current_tier = selected_bundle_tier()
    locked_services = {
        service.get("title")
        for service in SERVICES
        if not service_is_unlocked(service.get("title"), current_tier)
    }
    return render_template(
        "services.html",
        services=SERVICES,
        purchased=purchased,
        tier=current_tier,
        service_tier_map=SERVICE_TIER_MAP,
        locked_services=locked_services,
    )


@app.route("/buy/<service_name>")
def buy(service_name):
    # If service doesn't exist, redirect to services page
    if service_name not in SERVICES_BY_TITLE:
        return redirect(url_for("services"))

    current_tier = selected_bundle_tier()
    if not service_is_unlocked(service_name, current_tier):
        required_tier = SERVICE_TIER_MAP.get(service_name)
        session["celebration"] = (
            f"{service_name} unlocks at {required_tier} tier. Keep growing to add it."
        )
        return redirect(request.args.get("next") or url_for("tree"))

    # Add service to purchased list if not already there
    purchased = session.get("purchased", [])
    if service_name not in purchased:
        purchased.append(service_name)
    session["purchased"] = purchased

    # Add purchased service to growth tree if missing
    tree_data = session.get("growth_tree", default_tree())
    if service_name not in tree_data["year1"] + tree_data["year2"] + tree_data["year3"]:
        tree_data = add_service_to_tree(tree_data, service_name)
    session["growth_tree"] = merge_purchased_into_tree(tree_data, purchased)

    # Update tier and check for upgrade
    old_tier = session.get("tier")
    new_tier = calculate_tier()
    session["tier"] = new_tier
    if old_tier and old_tier != new_tier:
        session["celebration"] = f"Great work! You reached {new_tier} tier."

    # Rebuild recommendations when tier unlocks new service levels.
    if "quiz_answers" in session:
        session["growth_tree"] = generate_growth_tree(session["quiz_answers"])
        session["recommended_subservices"] = collect_recommended_subservices(
            session["quiz_answers"],
            all_bundle_services(),
        )

    # Redirect back to previous page or tree
    return redirect(request.args.get("next") or url_for("tree"))


@app.route("/select-bundle/<tier_name>")
def select_bundle(tier_name):
    # user chooses the starting bundle before taking the quiz
    if tier_name not in TIER_ORDER:
        return redirect(url_for("tier"))

    session["selected_bundle"] = tier_name
    session["tier"] = tier_name

    tier_to_years = {"Bronze": "1", "Silver": "2", "Gold": "3"}
    session["membership_years"] = tier_to_years.get(tier_name, "0")

    if "quiz_answers" in session:
        session["growth_tree"] = generate_growth_tree(session["quiz_answers"])
        session["recommended_subservices"] = collect_recommended_subservices(
            session["quiz_answers"],
            all_bundle_services(),
        )

    return redirect(url_for("quiz"))


@app.route("/tier")
def tier():
    # display user's current tier and progress
    current_tier = selected_bundle_tier()
    return render_template(
        "tier.html",
        tier=current_tier,
        progress=tier_progress_percent(),
        purchased_count=len(session.get("purchased", [])),
        years_with_cic=session.get("membership_years", "0"),
        tier_bundles=TIER_BUNDLES.get("tiers", []),
        general_bundle=RECOMMENDATION_RULES.get("general_bundle", []),
        has_quiz=bool(session.get("quiz_answers")),
        selected_bundle=session.get("selected_bundle"),
    )


@app.route("/invoice")
def invoice():
    # Show added services (no price tracking)
    items = purchased_details()
    return render_template("invoice.html", items=items)


if __name__ == "__main__":
    app.run(debug=True)
