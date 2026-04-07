# Project: Football Zone

## Project Overview
Football Zone is a FastAPI-based web application. The core reason for the project is that User can select teams 
from top X football leagues. User can see the next fixture, previous 5 results and AI analysis. The goal of this project
is to create a beautiful UI and connect it with AI backend. Goal is to have a strong project for Resume (Senior SWE)

## Architectural Mandates
- **Framework**: Use FastAPI for the backend.
- **Async/Await**: Prioritize asynchronous code for I/O operations.
- **Clean Architecture**: Maintain a clear separation between models, schemas, services, and routers.
- **Type Safety**: Use Pydantic models for request/response validation and Python type hints throughout the codebase.

## Development Workflows
- **Setup**: `pip install -r requirements.txt`
- **Run Application**: `uvicorn main:app --reload`
- **Testing**: [Add testing command here, e.g., `pytest`]
- **Linting**: [Add linting command here, e.g., `ruff check .` or `flake8`]

## Style & Quality Guidelines
- Follow PEP 8 style guidelines.
- Use descriptive variable and function names.
- Ensure all new features or bug fixes are accompanied by tests.
- Maintain comprehensive docstrings for all public modules, classes, and functions.
- Make sure code is well documented with READ me files and instructions to deploy if needed
