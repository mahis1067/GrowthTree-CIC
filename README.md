# GrowthTree-CIC

## Project Overview
The Circular Innovation Council is an organization funded solely by membership. Small businesses, municipalities, and large organizations can apply for CIC services to provide financial stability, research, policy updates, events, working collaboration, and visibility within the circular economy network. Membership is annual and fixed. 

The CIC Growth Tree is a new membership model which allows new small businesses to take a personalization quiz, which asks about the type of company they are, their goals in the circular economy, revenue, clientele, and more. This data is then processed with the CIC database of services, and a personalized roadmap is delivered. This roadmap tree will display the types of services the company can sign up for, personalized for them over multiple years. 

As the business follows the road map, or adds more services to the road map, the growth tree website should keep track of the services they bought and create a rank system, which gives more benefits like discounts, voting privileges, and recognition to businesses with high ranks and a high number of services applied for. 

## Target Audience
### 1. Public Institutions
These include schools and libraries.
Primary incentives: Informing and motivating students to educate them on environmental issues, using data for course material, and conducting research

Services they could benefit from: Access information, multi-sectoral perspectives, stay informed

### 2. Businesses
These include Retailers, brand owners and industry associations, recycling companies, and manufacturers.
Primary incentives: Developing sustainable practices for product innovation, packaging, and shipment, reducing their carbon footprint

Services they could benefit from: Network, access information, stay informed

### 3. Municipalities & Government
Primary incentives: Accelerating development of environmental projects by accessing specialized expertise, evaluating current environmental status with scientific research

Services they could benefit from: Access information, influence, stay informed

### 4. Associations & non-Profits
Primary incentives: Cross-referencing data, collaboration, extending their networks

Services they could benefit from: Network

### 5. Individuals
These include families, individuals, and students.
Primary incentives: Educating themselves on current environmental issues, working towards degrees, and building profiles

Services they could benefit from: Voting privileges, reduced rates, stay informed, and influence

## Skills Required
- HTML, CSS, Python Flask Library
- UX/UI Design
- Graphing Libraries (Matplotlib)
- Decision Trees

## Files and Directories
- Entities (folder): Hold images and visuals needed
- app.py: This will contain all the directories and back end python code, including python libraries to display graphs and visuals
- Quiz_questions (Folder)
> q1.html -> Each file is a new HTML code block which displays a new question in quiz.html
> q2.html
> q3.html
> q4.html
quiz.html    
- tree.html -> Main tree page, including classes for services, the main tree class
- Tree.html must include methods for adding services to the tree, evaluated the decision tree
- services.html -> Page with more services they can apply for, if bought from this page, the main tree should be updates
- Styles.css: Holds the main styling of everything
- Info.json: A detailed json file including a list of all the services like their title, images, prices, these can be made up as this is meant as a mock up

## Key Features
### Personalization Quiz
A quiz that asks the user necessary questions about their business to best see how their growth tree should be made. This quiz should be allowed to be taken at any time to change the tree. Services that have already been bought must stay in the new tree. 

### Growth Tree
An interactive tree that includes year 1, year 2, and so on, plans and services that can aid in the business. The user can, however, over a node in the tree to open a pop-up window of the service description, details, reviews and a buy button

### Tier Meter
A circular meter that keeps track of the types of services they signed up for. After completing certain services or buying services, they are given a ranking, which can give benefits for future services and recognition to CIC. This meter should be included in its own page with details and in the corner alongside the growth tree page.  

### InVoice
Keeps track of all the services that the business has bought over the years

### Services
A list of other services the business might want to buy that were not already in the growth tree. If the user buys from here, the new service is automatically added and adjusted to fit the tree

### Celebratory Messages
When the user acheives a new rank, a window will pop-up with a celebratory message praising their achievement.

## Future Improvements
- Sending out regular emails

## Decision Tree Recommendation Model (Detailed)

The personalization flow uses a **data-driven weighted decision tree**. Instead of hard-coding many `if/else` branches in Python, rules are defined in JSON and interpreted by the app.

### 1) Inputs used by the recommender

After the quiz is submitted, the app stores all answers and computes recommendations from:

- **Q1**: `organization_type` (first split)
- **Q6**: `event_type`
- **Q7**: `involvement_level`
- **Q8**: `year2_goal`

The app still collects **Q9** (`communication_style`) and keeps it on the page, but **Q9 is intentionally excluded** from recommendation scoring.

### 2) Candidate service pool

The model only scores services that are currently unlocked by the member's tier progression:

- Bronze members: Bronze services
- Silver members: Bronze + Silver services
- Gold members: Bronze + Silver + Gold services

This keeps recommendations realistic for what the member can access now.

### 3) Scoring stages

For each candidate service, the app computes a total score in layers:

1. **Tier base weight**
   - Every service starts with a base value from `tier_weight`.
   - This is where CIC can make a tier (like Silver) globally more attractive.

2. **Organization-type boost (Q1 split)**
   - `organization_type` is mapped to an internal category (e.g., `public_institution`, `small_business_nonprofit`).
   - The selected category applies predefined score boosts per service.
   - This is the first major branch in the decision tree.

3. **Intent/engagement boosts (Q6–Q8 splits)**
   - The model looks up rule tables for event preference, desired involvement, and year-2 outcome.
   - Each matching answer adds score boosts to relevant services.
   - These are additive, so a service aligned across multiple answers rises in rank.

Final score (per service) is effectively:

`tier_base + org_type_boost + q6_boost + q7_boost + q8_boost`

### 4) Converting scores into a 3-year roadmap

Once scores are computed:

1. Services are grouped by `preferred_year` (`year1`, `year2`, `year3`).
2. Within each year, services are sorted by score descending.
3. The app takes up to 3 positive-score services for that year.
4. If a year is sparse, fallback services are added so years are not empty.
5. Duplicates are removed while preserving order.
6. Any previously purchased services are merged back in so quiz retakes never erase purchased history.

### 5) Why this is modeled as a decision tree

Conceptually, this is a tree of decisions:

- **Root node**: member context + unlocked tiers
- **Branch 1**: organization type (segment intent)
- **Branch 2**: event preference
- **Branch 3**: involvement depth
- **Branch 4**: year-2 objective
- **Leaf output**: ranked services distributed across years

It is implemented as weighted rule tables (instead of deeply nested conditionals) so non-developers can tune behavior in JSON without changing Python code.

### 6) Tuning guidance for CIC admins

To adjust recommendation behavior:

- Edit `organization_boosts` to change how each organization segment is prioritized.
- Edit `question_boosts` to tighten/loosen service alignment for Q6–Q8 options.
- Edit `tier_weight` to make a tier more or less prominent globally.
- Keep service `preferred_year` values aligned with desired journey timing.

All of this can be changed in data files with no algorithm rewrite.
