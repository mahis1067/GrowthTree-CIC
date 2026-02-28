# GrowthTree-CIC

### Link to Website: https://mahi1067.pythonanywhere.com/

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

## Quiz-to-Service Mapping Recommendation Model

The personalization flow now uses a **direct quiz-to-service mapping model**. Each quiz option is mapped to one or more services in `entities/recommendation_rules.json`.

### 1) Inputs used by the recommender

After the quiz is submitted, the app stores all answers and uses all quiz fields:

- `organization_type`
- `primary_reason`
- `journey_stage`
- `governance_interest`
- `event_type`
- `involvement_level`
- `year2_goal`
- `communication_style`

### 2) Candidate service pool

The model only recommends services that are currently unlocked by the selected tier:

- Bronze bundle: Bronze services
- Silver bundle: Bronze + Silver services
- Gold bundle: Bronze + Silver + Gold services

### 3) Recommendation logic

1. Read each quiz answer.
2. Look up that answer in `option_service_map`.
3. Add a hit count for each mapped service.
4. Filter to services available in the selected bundle.
5. Sort matched services by tier progression first, then by hit count.
6. Place each service into its configured `preferred_year`.
7. Merge previously purchased services back into the growth tree.

If no quiz answers match a mapped service, the app falls back to showing all unlocked bundle services in their preferred years.

### 4) Tuning guidance for CIC admins

To adjust recommendation behavior, edit `entities/recommendation_rules.json`:

- `option_service_map`: controls which services each question option should recommend.
- `general_bundle`: controls tier descriptions shown on the tier page.

No Python algorithm rewrite is required to change recommendation behavior.
