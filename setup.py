import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="cpi_escalation_aus-tzam",
    version="0.0.1",
    author="Samuel Hyland",
    author_email="sam.copycat@gmail.com",
    description="Australian CPI escalation tool",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/Tzam/cpi_escalation_aus",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
)