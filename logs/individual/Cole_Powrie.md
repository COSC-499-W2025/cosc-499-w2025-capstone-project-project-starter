# Personal log of Cole Powrie (from Week 10)
## Applicable Date Range
- Monday, November 3rd to Sunday, November 9th

## Peer evaluation screenshot
![alt text](<imgs/ColePowrieW10.png>)

## This Milestone
- Improved database schema with better **cascading rules** and **unique constraints**
- Updated table structures to ensure referential integrity and automatic handling of record updates/deletions  
- Started work on verifying the successful setup and execution of the schema using **Docker Compose** with PostgreSQL and Python containers  

## Tasks
- Modified and tested schema setup scripts to include:  
  - `ON DELETE CASCADE` and `ON UPDATE CASCADE` relationships  
  - `UNIQUE` constraints to prevent duplicate entries  
- Verified successful database initialization and connection within the Docker environment  

## Progress from the Last Two Weeks
- Fixed/still working on setup issues with Docker and PostgreSQL integration  
- Enhanced data reliability through refined constraint and timestamp implementation  

## In Progress Tasks
- Testing backend CRUD operations under new cascading and constraint logic  
- Validating data persistence and behaviour on updates and deletions  

## Next Cycle Activities
- Connect backend endpoints to the updated schema  
- Integrate backend database operations with the ML pipeline and frontend  
- Continue expanding relationships and improving schema performance and maintainability  

# Personal log of Cole Powrie (from Week 9)
## Applicable Date Range
- Monday, October 27th to Sunday, November 2nd

## Peer evaluation screenshot
![alt text](<imgs/ColePowrieW9.png>)

## This Milestone
- Implemented proper database schema for our PostgreSQL setup  
- Added Users, Artifacts, and Category tables to structure our backend data  
- Established foreign key relationships between tables to link users, artifacts, and categories  
- Inserted 10 default general categories into the `category` table upon creation (subject to change as we identify our categories)

## Tasks
- Updated database initialization script (`setup_test_db.py`) to include:  
  - Creation of the `users`, `artifacts`, and `category` tables  
  - Establishment of a foreign key relationship between `artifacts.user_id` → `users.id`  
  - Addition of a foreign key between `artifacts.category_id` → `category.id`  
  - Automatic population of 10 general categories when the table is first created  

## Progress from the last two weeks
- Successfully connected to PostgreSQL via Python using `psycopg2`  
- Confirmed working connection through test table creation and queries  
- Transitioned from test tables to the start of relational structure for our project  

## In Progress Tasks
- Populating the tables with real project data (users, file uploads, etc.)  
- Integrating database interactions into our backend endpoints  

## Next Cycle Activities
- Expand the category system and artifact handling to support ML integration for file analysis
- Adding more relevant tables and furthering the relationships between them

# Personal log of Cole Powrie (from Week 8)
## Applicable Date Range
- Monday, October 20th to Sunday, October 26th

## Peer evaluation screenshot
![alt text](<imgs/ColePowrieW8.png>)

## This Milestone
- We continued work on our zip and file validator
- Researched and found a dataset to pre-train our ML model
- Started setting up our PostgreSQL and the connection to it

## Tasks
- Researching and identifying different datasets and methods of pre-training for our ML model
- Setting up a basic connection file to PostgreSQL, as well as implementing a test table to ensure proper connection

## Progress from the last two weeks
- We have made extensive progress on the training of our ML model
- Started a basic implementation of DB and the connection to it

## In Progress Tasks
- Adding values to our tables in our database and further setting up the DB

## Next Cycle Activities
- We will next continue on our backend code for our file handling
- Continue the integration and implementation of our DB

# Personal log of Cole Powrie (from Week 7)
## Applicable Date Range
- Monday, October 13th to Sunday, October 19th

## Peer evaluation screenshot
![alt text](<imgs/ColePowrieW7.png>)

## This Milestone
- Started work on our coding parser and our zip file validator
- Updated our ReadMe with our DFD level 1 and our system architecture design

## Tasks
- Start coding work on our backend for our file handling
- Update our ReadMe with our system information and DFD

## Progress from the last two weeks
- Our coding environment has been set up, and functional requirements are being worked on

## In Progress Tasks
- The backend code for our file processing and handling
- The start of our code for the parser

## Next Cycle Activities
- We will next continue on our backend code for our file handling

# Personal log of Cole Powrie (from Week 6)
## Applicable Date Range
- Monday, October 6th to Sunday, October 12th

## Peer evaluation screenshot
![alt text](<imgs/cole_powrie_w6.png>)

## This Milestone
- Finalized our DFDs
- Start setting up our coding environment
- Added pull request template

## Tasks
- Finalized and clarified our DFD using Figma
- Created a wireframe of how we expect the flow of our program to work to help with our backend organization

## Progress from the last two weeks
- Finalized our DFD, started our code and its enviroment, and made a wireframe

  
# Personal log of Cole Powrie (from Week 5)
## Applicable Date Range
- Monday, September 29th to Sunday, October 5th

## Peer evaluation screenshot
![alt text](<imgs/ColePowrieW5.png>)

## This Milestone
- We made our data flow diagram for our project
- We created our level 0 and level 1 data flow diagram and finalized our level 1 diagram

## Tasks
- Helped review for our DFD's

## Progress from the last two weeks
- From the last two weeks I helped with our DFD as well as create and organize our system architecture diagram with Figma
  
# Personal log of Cole Powrie (from Week 4)
## Applicable Date Range
- Monday, September 22nd to Sunday, September 28th

## Peer evaluation screenshot
![alt text](<imgs/cole_powrie_w3.png>)

## Recap On Your Weeks Goals
- Which Features Were Yours in the Project Plan for this Milestone?
  I helped with front end aspect for our project proposal as well as the system architecture diagram, which we did through .Fimga
- Which Tasks from the Project Board are Associtaed with these Features?
  We recorded these tasks as issues in our GitHub repository and made sure that we divided tasks evenly for the proposal and system architecture diagram.
- Among these tasks, which have you completed/in progress in the last 2 weeks?
  We completed our project proposal and system architecture diagram this week.
- Optional text: additional context that we should be aware of:
  Good communication and effort from everyone in the team!
  

# Personal log of Cole Powrie (from Week 3)


## What went well


- Discussion with other teams was insightful to see other peoples interpretations of the project outline
- Our discussion went smooth and everyone was on the same page for what we wanted our functional and non-functional requirements.


## What didn’t go well


- Difficulty and confusion in finding and talking with the other teams about their requirements




## Planning for the next cycle


- Completing our Project Proposal
- Completing our system architecture diagram



