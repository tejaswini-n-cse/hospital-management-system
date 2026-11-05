# 🏥 Hospital Management System

A full stack web app for managing patients, doctors and appointments, built with **Django, MySQL, HTML, CSS and JavaScript**.

> 🚧 Work in progress. New features are added step by step.

## Features so far

- Custom user model with roles (patient, doctor, admin)
- Patient registration, login and logout
- Role-based dashboards
- Departments, doctor profiles, availability and appointment models
- Customized Django admin panel
- MySQL database with secrets kept in a `.env` file

## Tech Used

Python, Django, MySQL, HTML, CSS, JavaScript

## How to Run Locally

```
git clone https://github.com/YOUR-USERNAME/hospital-management-system.git
cd hospital-management-system
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

1. Create a MySQL database named `hospital_db`.
2. Copy `.env.example` to `.env` and fill in your values.
3. Run:

```
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Author

**Tejaswini N**
GitHub: https://github.com/tejaswini-n-cse
