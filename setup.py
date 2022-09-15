import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="carta",
    version="1.1.6",
    author="Adrianna Pińska",
    author_email="adrianna.pinska@gmail.com",
    description="CARTA scripting wrapper written in Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/CARTAvis/carta-python",
    packages=["carta"],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: POSIX",
    ],
    python_requires='>=3.6',
    install_requires=[
        "requests",
        "simplejson",
    ],
    setup_requires=[
        "wheel",
    ],
)
