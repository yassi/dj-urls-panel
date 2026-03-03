# Configuration

Dj Urls Panel currently works out of the box with minimal configuration.

## Basic Setup

The only required configuration is adding the app to your `INSTALLED_APPS` and including the URLs in your URL configuration.

See the [Installation](installation.md) guide for setup instructions.

## URLs Configuration

```python
# urls.py
urlpatterns = [
    path('admin/dj-urls-panel/', include('dj_urls_panel.urls')),  # Custom path
    path('admin/', admin.site.urls),
]
```

## Security

Dj Urls Panel uses Django's built-in admin authentication:

- Only staff users (`is_staff=True`) can access the panel
- All views require authentication via `@staff_member_required`
- No additional security configuration needed

## CSS Customization

### `LOAD_DEFAULT_CSS`

**Type:** `bool`  
**Default:** `True`  
**Description:** Whether to load the built-in URLs Panel stylesheet. Set to `False` to use your own styles from scratch.

### `EXTRA_CSS`

**Type:** `list[str]`  
**Default:** `[]`  
**Description:** Additional stylesheets to load after the default CSS. Accepts static file paths or full URLs.

Static file paths are **relative to your app's `static/` subdirectory** (same convention as Django's `{% static %}` tag). A file at `myapp/static/myapp/css/overrides.css` is referenced as `myapp/css/overrides.css`.

```python
DJ_URLS_PANEL_SETTINGS = {
    'LOAD_DEFAULT_CSS': True,
    'EXTRA_CSS': [
        # File lives at: myapp/static/myapp/css/overrides.css
        'myapp/css/overrides.css',
        # Full URLs are also supported
        'https://cdn.example.com/theme.css',
    ],
}
```
