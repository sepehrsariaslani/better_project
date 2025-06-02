from setuptools import setup, find_packages

setup(
    name='better_project',
    version='0.0.1', # Make sure this matches the version in your __init__.py or hooks.py if you have one
    description='For managing the projects', # Add a description
    author='Sepehr', # Add your name
    author_email='Sepehrsariaslani@gmail.com', # Add your email
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=[
        # List any dependencies here, e.g., 'frappe>=15.0.0'
    ]
) 