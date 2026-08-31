from setuptools import setup, find_packages

setup(
    name="logpulse",
    version="1.0.0",
    author="Hermes Studio",
    description="Advanced log analyzer with filtering and reporting",
    packages=find_packages(),
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "logpulse=logpulse.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
    ],
)
