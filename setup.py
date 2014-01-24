import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages


setup(
    name = "clamp",
    version = "0.4",
    packages = find_packages(),
    entry_points = {
        "distutils.commands": [
            "build_jar = clamp.commands:build_jar_command",
            "clamp = clamp.commands:clamp_command",
            "singlejar = clamp.commands:singlejar_command",
        ],
        "distutils.setup_keywords": [
            "clamp = clamp.commands:parse_clamp_keyword",
        ],
        "console_scripts": [
            "singlejar = clamp.commands:singlejar_script_command",
        ]
    },
    zip_safe = True
)



