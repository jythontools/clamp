import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages


setup(
    name = "clamp",
    version = "0.1",
    packages = find_packages(),
    entry_points = {
        "distutils.commands": [
            "buildjar = clamp.build:buildjar",
        ],
        "distutils.setup_keywords": [
            "clamp = clamp.build:validate_clamp",
        ],
    }
)



