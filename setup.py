import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages


setup(
    name = "clamp",
    version = "0.4",
    packages = find_packages(),
    entry_points = {
        "distutils.commands": [
            "build_jar = clamp.commands:build_jar",
            "singlejar = clamp.commands:singlejar",
        ],
        "distutils.setup_keywords": [
            "clamp = clamp.commands:validate_clamp",
        ],
        "console_scripts": [
            "singlejar = clamp.commands:singlejar_command",
        ]
    }
)



