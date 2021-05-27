import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="oci-utils",
    version="0.0.1",
    author="Phil Wilkins",
    author_email="oci at mp3monster.org",
    description="A package for rapidly setting up developer users on OCI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mp3monster/oci-utilities",
    project_urls={
        "Bug Tracker": "https://github.com/mp3monster/oci-utilities/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache 2 License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "."},
    packages=setuptools.find_packages(where=","),
    python_requires=">=3.6",
)