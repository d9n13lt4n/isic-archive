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
    python_requires='>=3.6',
    install_requires=[
        'celery[redis]<5',
        # The latest cheroot suffers from https://github.com/cherrypy/cheroot/issues/317
        'cheroot==8.3.0',
        'geojson',
        'girder-large-image',
        'girder-gravatar',
        'girder>=3.0.2',
        'jsonpickle',
        'jsonschema',
        'large-image-source-tiff[girder]',
        'natsort',
        'numpy',
        'opencv-python==4.2.*',
        'pillow',
        'python-dateutil',
        'python-dotenv',
        'requests',
        'requests_toolbelt',
        'scikit-image',
        'scipy',
        'sentry-sdk',
    ],
    entry_points={
        'girder.plugin': [
            'isic_archive = isic_archive:IsicArchive'
        ]
    }
)
