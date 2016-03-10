from .base import *  # noqa

ALLOWED_HOSTS = ['.koombook.lan.', 'localhost', '127.0.0.1']
TIME_ZONE = None
DOMAIN = 'koombook.lan'
BACKUP_FORMAT = 'gztar'
IDEASCUBE_BODY_ID = 'koombook'
STAFF_HOME_CARDS = [c for c in STAFF_HOME_CARDS
                    if c['url'] in ['user_list', 'server:power',
                                    'server:backup', 'server:wifi']]

HOME_CARDS = STAFF_HOME_CARDS + [
    {
        'id': 'blog',
    },
    {
        'id': 'mediacenter',
    },
    {
        'id': 'bsfcampus',
    },
    {
        'id': 'wikipedia.old',
    },
    {
        'id': 'khanacademy',
    },
    {
        'id': 'wikisource.old',
    },
    {
        'id': 'vikidia.old',
    },
    {
        'id': 'gutenberg.old',
    },
    {
        'id': 'cpassorcier.old',
    },
    {
        'id': 'ted.old',
    },
    {
        'id': 'software',
    },
    {
        'id': 'ubuntudoc.old',
    },
]
