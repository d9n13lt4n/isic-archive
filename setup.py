from setuptools import find_packages, setup

setup(
    name='isic-archive',
    version='1.0.0',
    description='The ISIC Archive API server.',
    url='https://github.com/ImageMarkup/isic-archive',

    packages=find_packages(),
    package_data={
        'isic_archive': ['mail_templates/*.mako',
                         'license_templates/*.mako',
                         '*.mako',
                         'models/masterFeatures.json'],
    },
    install_requires=[
        'backports.csv',
        'celery[redis]',
        'geojson',
        'girder-large-image',
        'girder-gravatar',
        'girder-oauth',
        'girder>=3.0.0a2',
        'jsonpickle',
        'large-image-source-tiff[girder]',
        'natsort',
        'numpy',
        'opencv-python',
        'pillow',
        'python-dateutil',
        'python-dotenv',
        'requests',
        'requests_toolbelt',
        'scikit-image',
        'scipy',
        'sentry-sdk',
        'six',
    ],
    entry_points={
        'girder.plugin': [
            'isic_archive = isic_archive:IsicArchive'
        ]
    }
)