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
BUNDLE_PRICE_MAP = {
    "Bronze": 300,
    "Silver": 900,
    "Gold": 1200,
}
BUNDLE_SERVICE_DETAILS = {
    service.get("title"): service
    for tier in TIER_BUNDLES.get("tiers", [])
    for service in tier.get("services", [])
}
TIER_SUMMARY_MAP = {
    tier.get("name"): tier.get("summary", "General Services")
    for tier in TIER_BUNDLES.get("tiers", [])
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


def bundle_service_titles_for_tier(current_tier):
    unlocked = set(accessible_tiers(current_tier))
    titles = []
    for tier in TIER_BUNDLES.get("tiers", []):
        if tier.get("name") not in unlocked:
            continue
        for service in tier.get("services", []):
            title = service.get("title")
            if title and title not in titles:
                titles.append(title)
    return titles


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




def subservices_for_tree(tree, recommended_subservices, current_tier, purchased_services):
    tree_subservices = default_tree()
    max_recommendations_per_year = 3

    for year in YEAR_ORDER:
        seen = set()
        for service_name in tree.get(year, []):
            if len(tree_subservices[year]) >= max_recommendations_per_year:
                break

            matched = recommended_subservices.get(service_name)
            if matched:
                candidates = matched
            else:
                candidates = BUNDLE_SERVICE_DETAILS.get(service_name, {}).get("subservices", [])

            required_tier = SERVICE_TIER_MAP.get(service_name, "Bronze")
            service_group = TIER_SUMMARY_MAP.get(required_tier, "General Services")
            unlocked = service_is_unlocked(service_name, current_tier)
            added = service_name in purchased_services

            for subservice in candidates:
                if len(tree_subservices[year]) >= max_recommendations_per_year:
                    break
                if not subservice:
                    continue

                dedupe_key = f"{service_name}::{subservice}"
                if dedupe_key in seen:
                    continue

                tree_subservices[year].append(
                    {
                        "service": service_name,
                        "subservice": subservice,
                        "group": service_group,
                        "required_tier": required_tier,
                        "is_locked": not unlocked and not added,
                        "is_added": added,
                        "use_url": url_for("buy", service_name=service_name),
                    }
                )
                seen.add(dedupe_key)

    return tree_subservices

def calculate_tier():
    # Tier progression is based on time only.
    years_with_cic = int(session.get("membership_years", 0))

    if years_with_cic >= 3:
        return "Gold"
    if years_with_cic >= 2:
        return "Silver"
    if years_with_cic >= 1:
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
    recommended_subservices = session.get("recommended_subservices", {})
    tree_subservices = subservices_for_tree(
        tree_data,
        recommended_subservices,
        current_tier,
        set(purchased_names),
    )

    return render_template(
        "tree.html",
        tree=tree_subservices,
        tier=current_tier,
        progress=tier_progress_percent(),
        services_map=SERVICES_BY_TITLE,
        purchased=set(purchased_names),
        purchased_count=len(purchased_names),
        unlocked_count=len(SERVICE_TIER_MAP) - len(locked_services),
        celebration=celebration,
        locked_services=locked_services,
        service_tier_map=SERVICE_TIER_MAP,
        recommended_subservices=recommended_subservices,
    )


@app.route("/services")
def services():
    # Show bundle services as a reference catalog (visual guidance only).
    current_tier = selected_bundle_tier()
    return render_template(
        "services.html",
        tier_bundles=TIER_BUNDLES.get("tiers", []),
        tier=current_tier,
    )


@app.route("/buy/<service_name>")
def buy(service_name):
    # Service catalog is view-only; do not allow manual additions to the tree.
    session["celebration"] = "Service bundles are visual only in the tree. Select a tier bundle to shape your roadmap."
    return redirect(request.args.get("next") or url_for("services"))


@app.route("/buy-bundle/<tier_name>")
def buy_bundle(tier_name):
    # User buys/selects a starting bundle before taking the quiz
    if tier_name not in TIER_ORDER:
        return redirect(url_for("tier"))

    session["selected_bundle"] = tier_name
    bundle_price = BUNDLE_PRICE_MAP.get(tier_name, 0)
    session["bundle_purchase"] = {"name": tier_name, "price": bundle_price}
    session["celebration"] = f"{tier_name} bundle added for ${bundle_price}."

    tier_to_years = {"Bronze": "1", "Silver": "2", "Gold": "3"}
    session["membership_years"] = tier_to_years.get(tier_name, "0")
    session["tier"] = calculate_tier()

    purchased = session.get("purchased", [])
    for service_name in bundle_service_titles_for_tier(tier_name):
        if service_name not in purchased:
            purchased.append(service_name)
    session["purchased"] = purchased

    # Keep recommendation plan stable when users add more bundles.
    if "growth_tree" in session:
        session["growth_tree"] = merge_purchased_into_tree(session["growth_tree"], purchased)

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
        bundle_price_map=BUNDLE_PRICE_MAP,
        bundle_purchase=session.get("bundle_purchase"),
        current_bundle_price=BUNDLE_PRICE_MAP.get(session.get("selected_bundle"), 0),
    )


@app.route("/invoice")
def invoice():
    # Show added services (no price tracking)
    items = purchased_details()
    return render_template("invoice.html", items=items)


if __name__ == "__main__":
    app.run(debug=True)
