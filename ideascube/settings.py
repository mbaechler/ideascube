import importlib
import os
import re
import socket
import sys

# The normal scenario is that we use the hostname, but let's make it
# overridable, this is useful for dev and debugging.
IDEASCUBE_HOSTNAME = socket.gethostname()  # Store it for later use.
IDEASCUBE_ID = os.environ.get('IDEASCUBE_ID', IDEASCUBE_HOSTNAME)
IDEASCUBE_ID = re.sub('[^\w_]', '', IDEASCUBE_ID)
sys.stdout.write('IDEASCUBE_ID={}\n'.format(IDEASCUBE_ID))

# Every box will have some edge specific needs, such as a specific user model,
# we manage this with per box settings, but we want those specific settings
# to be versionned, for two reasons: easier to debug when there is no hidden
# local config, and easier to manage code upgrade.
try:
    sub = importlib.import_module(".conf." + IDEASCUBE_ID, package="ideascube")
except Exception as e:
    if not isinstance(e, ImportError):
        print(e)
    from .conf import dev as sub
finally:
    # Make it available as a settings, to be able to display it in the admin.
    SETTINGS_MODULE = sub.__name__
    sys.stdout.write('Importing settings from %s\n' % SETTINGS_MODULE)
    ldict = locals()
    for k in sub.__dict__:
        if k.isupper() and not k.startswith('__') or not k.endswith('__'):
            ldict[k] = sub.__dict__[k]
    USER_DATA_FIELDS = []
    for section, fields in USER_FORM_FIELDS:  # noqa
        USER_DATA_FIELDS.extend(fields)

    # Allow server settings to only define STORAGE_ROOT without needing to
    # redefine all ROOTS like settings.
    BACKUPED_ROOT = ldict.get('BACKUPED_ROOT') or os.path.join(STORAGE_ROOT, 'main')  # noqa
    MEDIA_ROOT = ldict.get('MEDIA_ROOT') or os.path.join(BACKUPED_ROOT, 'media')  # noqa
    STATIC_ROOT = ldict.get('STATIC_ROOT') or os.path.join(STORAGE_ROOT, 'static')  # noqa
    if not getattr(ldict, 'DATABASES', None):
        DATABASES = {
            'default': {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': os.path.join(BACKUPED_ROOT, 'default.sqlite'),
            },
        }
    LANGUAGES = []
    # Allow to override AVAILABLE_LANGUAGES in box settings, without needing
    # to override also LANGUAGES.
    for code, label in ldict.get('AVAILABLE_LANGUAGES'):
        LANGUAGES.append((code, label))
    # Some languages are missing from Django.
    from django.conf.locale import LANG_INFO
    LANG_INFO.update(EXTRA_LANG_INFO)  # noqa
