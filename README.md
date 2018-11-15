# bibtex2md

convert information from a bibTeX file into multiple markdown files suitable for use with hugo-academic

The `build_publications.py` Python 3 script builds a directory structure like
```
build
├── ucsc_fda
│   ├── cite.bib
│   ├── featured.png
│   └── index.md
├── ucsc_fpi
│   ├── cite.bib
│   └── index.md
└── ucsc_osaka
    ├── cite.bib
    └── index.md
```
that is suitable for use with hugo-academic to create the "publication" entries for the website (copy contents of `build/` into hugo's `content/publication/`). The entries for the `index.md` files and the `cite.bib` are generated from a bibTeX file that needs to be supplied and can be modified by entries in the `buildconfig.toml` configuration file.

## How it works

All that is required is a Python 3 installation with [toml](https://pypi.org/project/toml/) (JSON configuration files are also supported) and a bibTeX file containing the information of the publications that need to be included (Mendeley can create such a file).

# To build:
1. Edit the `buildconfig.toml` configuration file to point to the bibTeX file and include the publications to generate entries for. Information not contained in the bibTeX file (like abstracts) can also be supplied via `buildconfig.toml`. If both files contain information for an entry the one from the configuration file is used.
2. Edit `buildconfig.toml` to set the build directory in which the directory structure and files will be generated. *Be aware that files in the build direcory may be erased or overwritten.*  
3. Run `build_publications.py`.
4. Copy the contents of the build directory into hugo's `content/publication/` directory.

## Authors

* Jann Paul Mattern [jpmattern](https://github.com/jpmattern)

## License

This project is licensed under the Apache License - see the [LICENSE.md](LICENSE.md) file for details.
