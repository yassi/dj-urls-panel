# Installation

## 1. Install the Package

```bash
pip install dj-urls-panel
```

## 2. Add to Django Settings

Add `dj_urls_panel` to your `INSTALLED_APPS`:

```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'dj_urls_panel',  # Add this
    # ... your other apps
]
```

## 3. Include URLs

Add the Panel URLs to your main `urls.py`:

```python
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/dj-urls-panel/', include('dj_urls_panel.urls')),
    path('admin/', admin.site.urls),
]
```

## 4. Run Migrations

```bash
python manage.py migrate
```

## 5. Configure Settings (Optional)

For basic usage, no configuration is needed. For advanced features and security options:

```python
# settings.py
DJ_URLS_PANEL_SETTINGS = {
    # Exclude specific URL patterns
    'EXCLUDE_URLS': [
        r'^admin/',      # Exclude admin URLs
        r'^__debug__/',  # Exclude debug toolbar
    ],
    
    # Enable/disable URL testing interface
    'ENABLE_TESTING': True,  # Set to False in production
    
    # Whitelist hosts for URL testing (SSRF protection)
    'ALLOWED_HOSTS': None,  # or ['yourdomain.com']
}
```

See [Configuration](configuration.md) for detailed options.

## 6. Access the Panel

1. Start your Django development server:
   ```bash
   python manage.py runserver
   ```

2. Navigate to `http://127.0.0.1:8000/admin/`

3. Look for the "DJ URLS PANEL" section

That's it! You can now browse and test your URLs directly from the admin interface.
