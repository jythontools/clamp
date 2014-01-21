import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages


setup(
    name = "clamp",
    version = "0.3",
    packages = find_packages(),
    entry_points = {
        "distutils.commands": [
            "build_jar = clamp.build:build_jar",
            "singlejar = clamp.build:singlejar",
        ],
        "distutils.setup_keywords": [
            "clamp = clamp.build:validate_clamp",
        ],
        "console_scripts": [
            "singlejar = clamp.build:singlejar_command",
        ]
    }
)



