import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="blackcurve",
    version="0.1.5",
    author="BlackCurve LTD.",
    author_email="george.rowberry@blackcurve.com",
    description="An easy to use python interface for BlackCurve's API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/blackcurve/BlackCurve-API",
    packages=setuptools.find_packages(exclude=['tests']),

    classifiers=(
        "Programming Language :: Python",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ),
)