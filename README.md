[![Tests](https://github.com/yassi/dj-urls-panel/actions/workflows/test.yml/badge.svg)](https://github.com/yassi/dj-urls-panel/actions/workflows/test.yml)
[![codecov](https://codecov.io/gh/yassi/dj-urls-panel/branch/main/graph/badge.svg)](https://codecov.io/gh/yassi/dj-urls-panel)
[![PyPI version](https://badge.fury.io/py/dj-urls-panel.svg)](https://badge.fury.io/py/dj-urls-panel)
[![Python versions](https://img.shields.io/pypi/pyversions/dj-urls-panel.svg)](https://pypi.org/project/dj-urls-panel/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)




# Dj Urls Panel

Visualize Django URL routing inside the Django Admin, including patterns, views, namespaces, etc


## Docs

[https://yassi.github.io/dj-urls-panel/](https://yassi.github.io/dj-urls-panel/)

## Features

- **TBD**: Add your main features here


### Project Structure

```
dj-urls-panel/
├── dj_urls_panel/         # Main package
│   ├── templates/           # Django templates
│   ├── views.py             # Django views
│   └── urls.py              # URL patterns
├── example_project/         # Example Django project
├── tests/                   # Test suite
├── images/                  # Screenshots for README
└── requirements.txt         # Development dependencies
```

## Requirements

- Python 3.9+
- Django 4.2+



## Screenshots

### Django Admin Integration
Seamlessly integrated into your Django admin interface. A new section for dj-urls-panel
will appear in the same places where your models appear.

**NOTE:** This application does not actually introduce any model or migrations.

![Admin Home](https://raw.githubusercontent.com/yassi/dj-urls-panel/main/images/admin_home.png)


## Installation

### 1. Install the Package

```bash
pip install dj-urls-panel
```

### 2. Add to Django Settings

Add `dj_urls_panel` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dj_urls_panel',  # Add this line
    # ... your other apps
]
```

### 3. Configure Settings (Optional)

Add any custom configuration to your Django settings if needed:

```python
# Optional: Add custom settings for dj_urls_panel
DJ_URLS_PANEL_SETTINGS = {
    # Add your configuration here
}
```




### 4. Include URLs

Add the Panel URLs to your main `urls.py`:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/dj-urls-panel/', include('dj_urls_panel.urls')),  # Add this line
    path('admin/', admin.site.urls),
]
```

### 5. Run Migrations and Create Superuser

```bash
python manage.py migrate
python manage.py createsuperuser  # If you don't have an admin user
```

### 6. Access the Panel

1. Start your Django development server:
   ```bash
   python manage.py runserver
   ```

2. Navigate to the Django admin at `http://127.0.0.1:8000/admin/`

3. Look for the "DJ URLS PANEL" section in the admin interface



## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

## Development Setup

If you want to contribute to this project or set it up for local development:

### Prerequisites

- Python 3.9 or higher
- Redis server running locally
- Git
- Autoconf
- Docker

It is reccommended that you use docker since it will automate much of dev env setup

### 1. Clone the Repository

```bash
git clone https://github.com/yassi/dj-urls-panel.git
cd dj-urls-panel
```

### 2a. Set up dev environment using virtualenv

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -e . # install dj-urls-panel package locally
pip intall -r requirements.txt  # install all dev requirements

# Alternatively
make install # this will also do the above in one single command
```

### 2b. Set up dev environment using docker

```bash
make docker_up  # bring up all services (redis, memached) and dev environment container
make docker_shell  # open up a shell in the docker conatiner
```

### 3. Set Up Example Project

The repository includes an example Django project for development and testing

```bash
cd example_project
python manage.py migrate
python manage.py createsuperuser
```

### 4. Populate Test Data (Optional)

Add any custom management commands for populating test data if needed.

### 6. Run the Development Server

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/admin/` to access the Django admin with Dj Urls Panel.

### 7. Running Tests

The project includes a comprehensive test suite. You can run them by using make or
by invoking pytest directly:

```bash
# build and install all dev dependencies and run all tests inside of docker container
make test_docker

# Test without the docker on your host machine.
# note that testing always requires a redis and memcached service to be up.
# these are mostly easily brought up using docker
make test_local
```
