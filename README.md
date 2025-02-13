# Expense API Documentation

This document provides instructions on how to set up, run, and test the Expense API project. This API allows users to manage their personal expenses, with features for user authentication, expense creation, retrieval, updating, deletion, and filtering.

## Table of Contents

*   [Getting Started](#getting-started)
    *   [Prerequisites](#prerequisites)
    *   [Virtual Environment Setup](#virtual-environment-setup)
    *   [Install Dependencies](#install-dependencies)
    *   [Database Setup](#database-setup)
    *   [Secret Key Generation and Configuration](#secret-key-generation-and-configuration)
*   [Running the Application](#running-the-application)
*   [Testing the Application](#testing-the-application)
*   [API Endpoints](#api-endpoints)

## Getting Started

Follow these steps to set up your development environment and get the Expense API running.

### Prerequisites

Before you begin, ensure you have the following installed:

*   **Python 3.8+**:  Expense API is built using Python 3.8 or later. You can download Python from [python.org](https://www.python.org/downloads/).
*   **pip**:  pip is the package installer for Python. It is usually included with Python installations. You can check if you have pip installed by running `pip --version` in your terminal.

### Virtual Environment Setup

It's recommended to use a virtual environment to manage dependencies for your project in isolation.

1.  **Create a virtual environment:**

    Open your terminal in the project's root directory and run:

    ```bash
    python -m venv venv
    ```

    This command creates a virtual environment named `venv` in your project directory.

2.  **Activate the virtual environment:**

    *   **On Linux/macOS:**

        ```bash
        source venv/bin/activate
        ```

    *   **On Windows:**

        ```bash
        venv\Scripts\activate
        ```

    Once activated, you will see `(venv)` at the beginning of your terminal prompt, indicating that the virtual environment is active.

### Install dependencies from `requirements.txt`

    With your virtual environment activated, run:

    ```bash
    pip install -r requirements.txt
    ```

    This command will install all the necessary Python packages listed in `requirements.txt`.

### Database Setup

The Expense API uses SQLite for its database. The database file `database.db` will be automatically created in your project directory when you run the application for the first time.  SQLModel will handle the database creation and table setup based on the defined models in `models.py`.

No manual database setup is required.

### Secret Key Generation and Configuration

The API uses a secret key for JWT (JSON Web Token) signing. You need to generate a secure secret key and configure it in your application.

1.  **Generate a Secret Key:**

    Create a random secret key that will be used to sign the JWT tokens.

    To generate a secure random secret key use the command:

    ```bash
    openssl rand -hex 32
    ```

    It will print a securely generated secret key to your console. Copy this key.

2.  **Set the `SECRET_KEY` in your application:**

    Create a .env file:
    SECRET_KEY = **your secret key**

## Running the Application

To run the Expense API, use `uvicorn`, an ASGI server. Make sure your virtual environment is activated.

1.  **Start the application:**

    Open your terminal in the project's root directory and run:

    ```bash
    uvicorn main:app --reload
    ```

    You should see output in your terminal indicating that the server has started, usually on `http://127.0.0.1:8000` or `http://localhost:8000`.

2.  **Access the API documentation:**

    FastAPI automatically generates interactive API documentation using Swagger UI and ReDoc. You can access it at:

    **Swagger UI:**  `http://localhost:8000/docs`

    Use these documentation interfaces to explore the API endpoints and interact with them.

## Testing the Application

The project includes a comprehensive test suite using `pytest`. Ensure your virtual environment is activated.

1.  **Run the tests:**

    Open your terminal in the project's root directory and run:

    ```bash
    pytest -v tests/
    ```

    pytest will discover and run all tests in the `tests` directory. You should see the test results in your terminal, indicating whether all tests passed.

## API Endpoints

Here is a brief overview of the main API endpoints:

**User Endpoints:**

*   **`POST /users/register`**: Register a new user.
*   **`POST /users/login`**: Log in and get an access token.
*   **`GET /users/me`**: Get information about the currently logged-in user.

**Expense Endpoints:**

*   **`POST /expenses`**: Create a new expense.
*   **`GET /expenses`**: Get a list of expenses (supports filtering and pagination).
*   **`GET /expenses/{expense_id}`**: Get a specific expense by ID.
*   **`PUT /expenses/{expense_id}`**: Update an existing expense.
*   **`DELETE /expenses/{expense_id}`**: Delete an expense.

---

This documentation should help you get started with setting up, running, and testing the Expense API project. For more detailed information about each endpoint, please refer to the automatically generated API documentation at `/docs` and `/redoc` when the application is running.