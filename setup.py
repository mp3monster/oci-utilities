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
    keywords='OCI Oracle Cloud Developers configuration',
    url="https://github.com/mp3monster/oci-utilities",
    project_urls={
        "Bug Tracker": "https://github.com/mp3monster/oci-utilities/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache 2 License",
        "Operating System :: OS Independent",
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
    ],
    package_dir={"": "."},
    packages=setuptools.find_packages(where=","),
    python_requires=">=3.9",
    install_requires=['oci'],
    package_data={'config': ['example-connection.properties'],
                            ['logging.properties']},
)