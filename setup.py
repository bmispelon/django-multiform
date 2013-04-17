from setuptools import setup, find_packages

setup(
    name="django-multiform",
    version="0.1",
    description="Wrap several django forms into one form-like object",
    keywords="django, forms, multiform",
    author="Baptiste Mispelon",
    author_email="bmispelon@gmail.com",
    license="MIT",
    url="https://github.com/bmispelon/django-multiform",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
       "Operating System :: OS Independent",
       "License :: OSI Approved :: MIT License",
       "Intended Audience :: Developers",
       "Programming Language :: Python :: 2.6",
       "Programming Language :: Python :: 2.7",
       "Programming Language :: Python :: 3.2",
       "Programming Language :: Python :: 3.3",
    ]
)
