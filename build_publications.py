#!/usr/bin/env python3
'''
Convert information contained in a bibtex bibliography to a series of markdown files.
'''

import os
import re
import datetime
from shutil import copyfile
from dateutil.parser import parse


def parse_bibtex_entry(bibtexfile, bibtexkey, firstnamefirst=True, typekey='type'):
    '''
    Extracts an entry from a bibtex file and returns it as a dictionary.

    Parameters
    ----------
    bibtexfile : str
        the name of a bibtex file
    bibtexkey : str
        the name of a bibtex entry, for which to extract information
    firstnamefirst : bool
        if set to true, return authors as "Jane Doe", else leave them as "Doe, Jane"
    typekey : str
        the key used to store the type of the publication, e.g. "article" for an @article entry

    Returns
    -------
    bibdata : dict
        dictionary containing the bibtex information for `bibtexkey`
    '''
    with open(bibtexfile) as f:
        # (?:...)  Non-grouping version of regular parentheses.
        pattern = r'^@(?P<type>[a-z]+) *{ *' + bibtexkey + r'(?P<options>(?: *,\s*\w+ * = *{(?:{[^}]+}|[^{}]+)+})+)'
        match_bib = re.search(pattern, f.read(), flags=re.MULTILINE)
    if match_bib is None:
        raise KeyError('Cannot find bibtex entry with key "{}" in "{}".'.format(bibtexkey, bibtexfile))

    bibtexdict = {typekey: match_bib.group('type').lower()}

    # parse the key-value pairs contained in options
    for keyvalue in re.split(',\n', match_bib.group('options')):
        tmp = re.split(' *= *', keyvalue, maxsplit=1)
        if len(tmp) == 1:
            continue
        # remove outermost "{}" for value
        bibtexdict[tmp[0].strip()] = tmp[1].strip()[1:-1]

    # process authors
    if 'author' in bibtexdict:
        authors = []
        for author in bibtexdict['author'].strip(' {}').split('and'):
            if firstnamefirst and ',' in author:
                # Mattern, Jann Paul -> Jann Paul Mattern
                author = ' '.join(reversed(author.split(',')))
            while '  ' in author:
                author = author.replace('  ', ' ')
            authors.append(author.strip())
        bibtexdict['author'] = authors

    return bibtexdict


def build_publications(configfile, bibtexfile=None, verbose=False):
    '''
    Extracts information from a bibtex file and builds a directory and file structure based on configuration
    in `configfile`.

    Parameters
    ----------
    configfile : str
        the name of a configuration file
    bibtexfile : str
        the name of a bibtex file
    verbose : bool
        print more information
    '''
    if verbose:
        print(' - reading configuration file "{}"'.format(configfile))
    if configfile.endswith('.json'):
        import json
        with open(configfile) as f:
            data = json.loads(f.read())
    else:
        import toml
        with open(configfile) as f:
            data = toml.loads(f.read())

    # load parameters from configuration
    if verbose:
        print('   loading parameters from configuration')
    try:
        if bibtexfile is None:
            bibtexfile = data['bibtexfile']
        builddir = data['builddir']
        defaults = data['defaults']
        url_pdf_usedoi = data['url_pdf_usedoi']
        publications = data['publications']
        citebibtexentries = data['citebibtexentries']

        publicationtype_mapping = data['publicationtype_mapping']
        header = data['partials']['header']
        footer = data['partials']['footer']
    except KeyError as ke:
        raise KeyError('Cannot find required entry "{}" in configuration file "{}".'.format(ke.args[0], configfile))

    for pubkey in publications:
        # create dir
        cdir = os.path.join(builddir, pubkey)
        os.makedirs(cdir, exist_ok=True)

        # extract associated bibtex entry
        if 'bibtexkey' in publications[pubkey]:
            bibtexkey = publications[pubkey]['bibtexkey']
        else:
            # if no bibtexkey is specified, pubkey is assumed to be bibtexkey
            bibtexkey = pubkey

        if verbose:
            print(' - building entries for publication "{}" (bibtex key: "{}")'.format(pubkey, bibtexkey))

        if verbose:
            print('   parsing information from bibtex file ("{}")'.format(bibtexfile))

        bibtexdict = parse_bibtex_entry(bibtexfile, bibtexkey)
        if len(bibtexdict) == 1 and 'abstract' in bibtexdict:
            raise ValueError('''Only the abstract was obtained from "{0}" for the key "{1}".
Ensure that the abstract contains no closing braces "}}" without opening ones "{{".
Possible workaround if the error persists:
Modify or eliminate abstract from "{0}" and add it to the configuration file "{2}" instead.'''.format(bibtexfile,
                                                                                                      bibtexkey,
                                                                                                      configfile))

        filename_index = os.path.join(cdir, 'index.md')
        filename_cite = os.path.join(cdir, 'cite.bib')

        with open(filename_index, 'w') as f:
            f.write(header)

            # title
            if 'title' in publications[pubkey]:
                title = publications[pubkey]['title']
            elif 'title' in bibtexdict:
                title = bibtexdict['title'].strip(' {}')
            else:
                raise ValueError('Cannot find "title" information for "{}" ({}).'.format(pubkey, bibtexkey))
            f.write('title = "{}"\n'.format(title))

            # date
            if 'date' in publications[pubkey]:
                date = publications[pubkey]['date']
            else:
                year = bibtexdict.get('year', datetime.datetime.now().year)
                month = bibtexdict.get('month', 1)
                day = bibtexdict.get('day', 1)
                try:
                    date = datetime.datetime(int(year), int(month), int(day)).isoformat(timespec='seconds')
                except (ValueError, TypeError):
                    date = parse('{} {} {}'.format(month, day, year)).isoformat(timespec='seconds')
            f.write('date = "{}"\n'.format(date))

            # authors
            if 'authors' in publications[pubkey]:
                authors = publications[pubkey]['authors']
            elif 'author' in bibtexdict:
                authors = bibtexdict['author']
            else:
                raise ValueError('Cannot find "authors" information for "{}" ({}).'.format(pubkey, bibtexkey))
            f.write('authors = ["{}"]\n'.format('", "'.join(authors)))

            # publication type
            if 'publication_types' in publications[pubkey]:
                if isinstance(publications[pubkey]['publication_types'], int):
                    publication_types = [publications[pubkey]['publication_types']]
                else:
                    publication_types = publications[pubkey]
            elif bibtexdict['type'] in publicationtype_mapping:
                publication_types = [publicationtype_mapping[bibtexdict['type']]]
            else:
                publication_types = 0  # uncategorized
            f.write('publication_types = ["{}"]\n'.format('", "'.join([str(i) for i in publication_types])))

            # Publication name and optional abbreviated version.
            if 'publication' in publications[pubkey]:
                publication = publications[pubkey]['publication']
            elif 'journal' in bibtexdict:
                publication = 'in *{}*'.format(bibtexdict['journal'])
            else:
                raise ValueError('Cannot find "publications" information for "{}" ({}).'.format(pubkey, bibtexkey))
            f.write('publication = "{}"\n'.format(publication))

            if 'publication_short' in publications[pubkey]:
                f.write('publication_short = "{}"\n'.format(publications[pubkey]['publication_short']))

            # Abstract and optional shortened version.
            if 'abstract' in publications[pubkey]:
                abstract = publications[pubkey]['abstract']
            elif 'abstract' in bibtexdict:
                abstract = bibtexdict['abstract'].replace('"', '\\"')
            else:
                raise ValueError('Cannot find "abstract" information for "{}" ({}).'.format(pubkey, bibtexkey))
            abstract = abstract.replace(r'{\%}', '%')
            f.write('abstract = "{}"\n'.format(abstract))

            if 'abstract_short' in publications[pubkey]:
                f.write('abstract_short = "{}"\n'.format(publications[pubkey]['abstract_short']))

            # featured
            if 'featured' in publications[pubkey]:
                featured = publications[pubkey]['featured']
            else:
                featured = defaults['featured']
            f.write('featured = {}\n'.format({True: 'true', False: 'false'}[featured]))

            # projects
            if 'projects' in publications[pubkey]:
                projects = publications[pubkey]['projects']
            else:
                projects = []
            f.write('projects = [{}]\n'.format(', '.join('"{}"'.format(s) for s in projects)))

            # tags
            if 'tags' in publications[pubkey]:
                tags = publications[pubkey]['tags']
            else:
                tags = []
            f.write('tags = [{}]\n'.format(', '.join('"{}"'.format(s) for s in tags)))

            # obtain doi
            if 'doi' in publications[pubkey]:
                doi = publications[pubkey]['doi']
            elif 'doi' in bibtexdict:
                doi = bibtexdict['doi']
            else:
                raise ValueError('Cannot find "doi" information for "{}" ({}).'.format(pubkey, bibtexkey))
            if verbose:
                print('   DOI: "{}"'.format(doi))

            # urls "url_*"
            urls = {k: publications[pubkey][k] for k in publications[pubkey] if k.startswith('url_')}
            if 'url_pdf' not in urls and url_pdf_usedoi and doi is not None:
                urls['url_pdf'] = 'https://doi.org/{}'.format(doi)
            for key, val in urls.items():
                f.write('{} = "{}"\n'.format(key, val))

            # write doi
            f.write('doi = "{}"\n'.format(doi))

            # math
            if 'math' in publications[pubkey]:
                math = publications[pubkey]['math']
            else:
                math = defaults['math']
            f.write('math = {}\n'.format({True: 'true', False: 'false'}[math]))

            f.write(footer)

        # write bibtexfile for "cite" button
        with open(filename_cite, 'w') as f:
            f.write('@{:s}{{{:s}\n'.format(bibtexdict['type'], bibtexkey))
            first = True
            for key in citebibtexentries:
                if key in bibtexdict:
                    if first:
                        first = False
                    else:
                        f.write(', \n')
                    f.write('    {} = {{{}}}'.format(key, bibtexdict[key]))

            f.write('\n}\n')

        # add image
        if 'image' in publications[pubkey]:
            fname_image = publications[pubkey]['image']
            ext = os.path.splitext(fname_image)[-1].lower()
            if verbose:
                print('   adding "{}" as image for this publication'.format(fname_image))
                if ext not in ('.png', '.jpg'):
                    print(' ! extension "{}" may not be supported, image might not show'.format(ext))
            copyfile(fname_image, os.path.join(cdir, 'featured'+ext))


if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Create directory structure and markdown (md) files for the "publication" section of a hugo academic website from a bibtext file.')
    parser.add_argument('--configfile', type=str, default='buildconfig.toml', help='A configuration file specifying the information to include in the build (default: "buildconfig.toml").')
    parser.add_argument('--bibtexfile', type=str, default=None, help='The bibtex file to obtain the publication information from (default: use bibtex file specified in CONFIGFILE).')
    parser.add_argument('--quiet', '-q', action='store_true', help='Do no print additional information while building.')

    args = parser.parse_args()

    build_publications(configfile=args.configfile, bibtexfile=args.bibtexfile, verbose=not args.quiet)

