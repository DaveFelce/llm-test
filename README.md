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
1. Write unit tests. At the moment, only integration tests are written.
2. Write a LOT more tests for the pubmed client and the services
3. Use Entrez library for PubMed API calls instead of the custom `PubMedClient` class

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