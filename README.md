# Covid Trends app

### Building and running the project
1. `docker compose up --build`

### Adding a superuser for the Admin page
1. `docker compose exec web sh`
2. `python manage.py createsuperuser`
3. Enter username, email and password to use to login to http://0.0.0.0:8000/admin

### To create and run migrations on a models change
1. `docker compose exec web python manage.py makemigrations data_pipeline`
2. `docker compose exec web python manage.py migrate`
3. `docker compose restart web`

### running the unit/integration tests
1. `docker compose exec web pytest`

## Technologies used and the reasoning behind them
1. **Django**: A high-level Python web framework that encourages rapid development and clean, pragmatic design.
2. **PostgreSQL**: A powerful, open-source object-relational database system, chosen for its robustness and scalability.
3. **Docker**: A platform for developing, shipping, and running applications in containers, ensuring consistency across different environments.
4. **pytest**: A testing framework for Python that makes it easy to write simple and scalable test cases.
5. **Django Admin**: A built-in feature of Django that provides a web-based interface for managing application data, making it easy to view and manipulate database records.

## TODO
1. Write unit tests. At the moment, only integration tests are written for the commands
2. Write a LOT more tests for the pubmed client and the services
3. Use Entrez library for PubMed API calls instead of the custom `PubMedClient` class
4. Use jinja2 templates for the prompts, load the examples and interpolate them into the prompt.

For testing the LLM calls, a set of fixtures could be provided in the `fixtures` directory.  The system prompt 
is the overall instructions for the llm separate from this specific example, the prompt is the current
example to work from. The test runs just this llm on the entries found in test-fixtures.json (which you can
just save from running the previous steps) coupled with the intended outputs.

```text
summary_judge_claim_check/
  fixtures/
    examples.json
    test-fixtures.json
  agent.py
  system-prompt.jinja
  prompt.jinja
  models.py
  test_agent.py
```

## High level architecture diagram

```text
                         +------------------------+
                         |    docker-compose       |
                         |  ┌────────┐  ┌───────┐  |
                         |  │  web   │  │  db   │  |
                         |  └────────┘  └───────┘  |
                         +-----------┬-------------+
                                     │
                                     ▼
                            +----------------+
                            |  Web Container |
                            | (Django App)   |
                            +----------------+
                                     │
          ┌──────────────────────────┼──────────────────────────┐
          │                          │                          │
          ▼                          ▼                          ▼
+------------------+        +------------------+        +------------------+
| Management       |        | Services Layer   |        | Models (ORM)     |
| Commands (CLI)   |        | – PubMedClient   |        | – Article        |
| – fetch_data     |        | – LLMOrchestrator|        | – Summary        |
| – summarize      |        | – FactChecker    |        | – Validation     |
| – validate       |        +------------------+        | – TrendReport    |
| – synthesize     |                                    +------------------+
+------------------+                           │
          │                                    │
          ▼                                    ▼
   (invokes HTTP)                       (invokes LLM API)
          │                                    │
+------------------+                +------------------+
| NCBI E-utilities |                |  OpenAI API      |
| (PubMed esearch/ |                | (GPT-3.5-Turbo)  |
|  efetch XML)     |                +------------------+
+------------------+                           
          │                                    │
          └───────────────────┬────────────────┘
                              ▼
                       +---------------+
                       |  Postgres     |
                       | (Articles,    |
                       |  Summaries,   |
                       |  Validations, |
                       |  TrendReports)|
                       +---------------+
```

## Possible deployment options

```text
+----------------+                           +------------------+           
|  EventBridge   |───on-schedule or manual──►|  Step Functions  |◄───┐
| (cron trigger) |                           | State Machine    |    │
+----------------+                           +------------------+    │
        │                                             │              │
        │                                             ▼              │
        │           +────────────────────────+   success?            │
        └────────►  |  RunTask: fetch_data   | ──────────────────────┘
                    |  (ECS Fargate task)    |
                    +────────────────────────+  
                                  │
                                  ▼
                    +────────────────────────+
                    |  RunTask: summarize    |
                    +────────────────────────+
                                  │
                                  ▼
                    +────────────────────────+
                    |  RunTask: validate     |
                    +────────────────────────+
                                  │
                                  ▼
                    +────────────────────────+
                    |  RunTask: synthesize   |
                    +────────────────────────+
                                  │
                                  ▼
                    +────────────────────────+
                    |  (Optional) Notify via │
                    |  SNS / Slack / Email   |
                    +────────────────────────+
```
	1.	Containerized tasks (ECS Fargate)
	2.	Step Functions for orchestration
	3.	EventBridge (or manual trigger) to kick off the workflow
	4.	RDS for Postgres and Secrets Manager (or Parameter Store) for credentials

	1.	Build and publish the Docker image
	•	Build a single image containing your Django app + management commands.
	•	Store credentials (DATABASE_URL, OPENAI_API_KEY, etc.) in AWS Secrets Manager or Parameter Store.
	•	Push the image to ECR.

	2.	Set up Postgres on RDS
	•	One RDS instance or cluster for your production database.
	•	Grant network access only to your ECS tasks (via VPC + security groups).

	3.	Define ECS Task Definitions
	•	One task definition (same container) but with different command: overrides:
	•	python manage.py fetch_data
	•	python manage.py summarize
	•	python manage.py validate
	•	python manage.py synthesize
	•	Each task reads its env vars (DB URL, API key) from Secrets Manager.

	4.	Orchestrate with Step Functions
	•	Create a Step Functions state machine with four RunTask steps.
	•	Configure “Retry” and “Catch” behavior on each step so failures can trigger alerts or retries.
	•	By default it will only move to the next step when the prior ECS task returns a 0 exit code.

	5.	Schedule or Trigger
	•	Use EventBridge (cron rule) to execute your state machine on whatever cadence you need (daily, hourly, etc.).
	•	Or run the state machine on‐demand via the AWS Console, SDK, or a CI/CD pipeline.

	6.	Monitoring & Notifications
	•	CloudWatch Logs automatically collect stdout/stderr from each ECS task.
	•	Alarms on Step Functions failures (or on unusually high latency) can fire SNS notifications.
