#!/usr/bin/env python

from __future__ import print_function

import argparse
import json
from json import JSONEncoder,JSONDecoder
import os
import subprocess
import sys

""" This is a utility to manage an OE build directory.
"""

class BBLayerSerializer:
    """ Class to serialize a collection of Repo objects into bblayer form.
    """
    def __init__(self, base, repos=[]):
        """ Initialize class.

        base: Directory component relative to TOPDIR where repos live.
              For repos in ${TOPDIR}/repos the base would be 'repos'.
        repos: An optional list of Repo objects. These objects hold all the
               interesting data that's written to the bblayers.conf file.
        """
        self._base = base
        self._repos = []
        for repo in repos:
            if type(repo) is Repo:
                self._repos.append(repo)
            else:
                raise TypeError
    def add_repo(self, repo):
        """ Add Repo object to be written to the bblayers.conf file.

        repo: The Repo object that's being added to the BBLayerSerializer.
        """
        self._repos.append(repo)
    def write(self, fd=sys.stdout):
        """ Write the bblayers.conf file to the specified file object.

        fd: A file object where the bblayer.conf file will be written.
            The default is sys.stdout.
        """
        fd.write("LCONF_VERSION ?= \"5\"\n")
        fd.write("BBPATH ?= \"${TOPDIR}\"\n")
        fd.write("BBLAYERS ?= \" \\\n")
        for repo in self._repos:
            if repo._layers is not None:
                for layer in repo._layers:
                    fd.write("    ${{TOPDIR}}/{0}/{1}/{2} \\\n".format(self._base, repo._name, layer))
        fd.write("\"\n")

class RepoFetcher(object):
    """ Class to manage git repo state.
    """
    def __init__(self, base, repos=[]):
        """ Initialize class.

        base: Directory where repos will or currently do reside.
        repos: List of Repo objects for the RepoFetcher to operate on.
        """
        self._base = base
        self._repos = []
        for repo in repos:
            if type(repo) is Repo:
                self._repos.append(repo)
            else:
                raise TypeError
    def add_repo(self, repo):
        """ Add a repo to the RepoFetcher.
        """
        self._repos.append(repo)
    def __str__(self):
        """ Create a string representation of all Repos in the RepoFetcher.
        """
        return ''.join(str(repo) for repo in self._repos)
    def clone(self):
        """ Clone all repos in a RepoFetcher.

        Does nothing more than loop over the list of Repo objects invoking the
        'clone' method on each.
        """
        for repo in self._repos:
            repo.clone(self._base)

class Repo(object):
    """ Data required to clone a git repo in a specific state.
    """
    def __init__(self, name, url, branch="master", revision="head", layers=["./"]):
        """ Initialize Repo object.

        name: Sting name of the repo.
        url: URL where git repo lives.
        brance: Branch that will be checked out. Default is 'master'.
        revision: Revision where HEAD should point. Default is 'HEAD'.
        layers: A list of the OE meta-layers in the repo that we care about.
                By default we assume the base of the repo is the root of the
                meta layer but in some cases the repo may contain many, or none
                at all. In this last case layers should be set to None.
        """
        self._name = name
        self._url = url
        self._branch = branch
        self._revision = revision
        self._layers = layers
    def set_branch(self, branch):
        """ Set branch for Repo object.
        """
        self._branch = branch
    def set_revision(self, revision):
        """ Set revision for Repo object.
        """
        self._revision = revision
    def set_layers(self, layers):
        """ Set the list of layers for the Repo ojbect.
        """
        self._layers = layers
    def __str__(self):
        """ Create a human readable string representation of the Repo object.
        """
        return ("name:     {0}\n"
                "url:      {1}\n"
                "branch:   {2}\n"
                "revision: {3}\n"
                "layers:   {4}\n".format(self._name, self._url, self._branch,
                                         self._revision,self._layers))
    def clone(self, path):
        """ Clone the Repo.

        path: Path where Repo will be cloned. If renative it will be relative
              to $(pwd).
        """
        dest = path + "/" + self._name
        try:
            if not os.path.exists(dest):
                print("cloning {0} into {1}".format (self._name, path))
                return subprocess.call(
                    ['git', 'clone', '--progress', self._url, dest], shell=False
                )
            else:
                return 1
        except subprocess.CalledProcessError, e:
            print(e)
 
class FetcherEncoder(JSONEncoder):
    """ Encode RepoFetcher object as JSON

    Pass this class to the dumps function from the json module along with your
    RepoFetcher object.
    """
    def default(self, obj):
        """ Iterate over repo objects from RepoFetcher encoding each as JSON.
            Return the result in a list.

        obj: RepoFetcher that's being encoded as JSON.
        """
        if type(obj) is not RepoFetcher:
            raise TypeError
        if obj._repos is None:
            raise ValueError
        list_tmp = []
        for repo in obj._repos:
            list_tmp.append(RepoEncoder().default(repo))
        return list_tmp

class RepoEncoder(JSONEncoder): 
    """ Encode a Repo object as JSON

    Pass this class to the dumps function from the json module along with your
    Repo object.
    """
    def default(self, obj):
        """ Encode a Repo object into a form suitable for serialization as
            JSON. Basically this turns the Repo object into a native python
            dictionary since those can be serialized to JSON.

        obj: Repo object to be encoded.
        """
        if type(obj) is not Repo:
            raise TypeError
        dict_tmp = {}
        dict_tmp["name"] = obj._name
        dict_tmp["url"] = obj._url
        if obj._branch != "master":
            dict_tmp["branch"] = obj._branch
        if obj._layers is None:
            dict_tmp["layers"] = obj._layers
        elif len(obj._layers) > 1 or obj._layers[0] != "./":
            dict_tmp["layers"] = obj._layers
        return dict_tmp

def repo_decode(json_obj):
    """ Create a repository object from a dictionary.

    Intended for use in JSON deserialization.
    json_obj: A dictionary object that contains a serialized Repo object.
    """
    if type(json_obj) is not dict:
        raise TypeError
    return Repo(json_obj["name"],
                     json_obj["url"],
                     json_obj.get("branch", "master"),
                     json_obj.get("revision", "HEAD"),
                     json_obj.get("layers", ["./"]))

def manifest(args):
    """ Create manifest in JSON describing current state of repos.
    """
    repo_json = args.repos_json
    src_dir = args.src_dir

    print("repo_json: {0}".format(repo_json))
    print("src_dir: {0}".format(src_dir))
    # Create Repo objects from repos in src_dir
    fetcher = RepoFetcher(src_dir)
    subdirs = os.listdir(src_dir)
    for item in subdirs:
        repo_root = os.path.join(src_dir, item)
        git_dir = os.path.join(repo_root, ".git")
        # check that directory is a git repo
        if os.path.isdir(git_dir):
            # collect data from git repo
            rev = subprocess.check_output(
                ["git", "rev-parse", "HEAD"]
            ).rstrip()
            branch = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"]
            ).rstrip()
            remote = subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]
            ).split("/")[0].rstrip()
            url = subprocess.check_output(
                ["git", "config", "--get", "remote." + remote + ".url"]
            ).rstrip()
            fetcher.add_repo(Repo(item, url, branch=branch, revision=rev))
        else:
            print("Not a git repo, skipping: {0}".format(git_dir))
    # Serialize Repo objects to JSON manifest
    with open(repo_json, 'w') as repo_json_fd:
        json.dump(fetcher, repo_json_fd, indent=4, cls=FetcherEncoder)
    return

def setup(args):
    """ Setup build structure.
    """
    conf_dir = args.conf_dir
    repo_json = args.repos_json
    src_dir = args.src_dir

    bblayers_file = conf_dir + "/bblayers.conf"
    # Parse JSON file with repo data
    with open(repo_json, 'r') as repos_fd:
        while True:
            try:
                repos = JSONDecoder(object_hook=repo_decode).decode(repos_fd.read())
                fetcher = RepoFetcher(src_dir, repos=repos)
            except ValueError:
                break;
    # fetch repos
    if not os.path.isdir(src_dir):
        os.mkdir(src_dir)
    fetcher.clone()
    # create bblayers.conf file, don't overwrite
    if not os.path.isdir(conf_dir):
        os.mkdir(conf_dir)
    bblayers = BBLayerSerializer(src_dir, repos=fetcher._repos)
    if os.path.exists(bblayers_file):
        raise ValueError(bblayers_file + " already exists");
    with open(bblayers_file, 'w') as test_file:
        bblayers.write(fd=test_file)
    return

"""
    print("serializing a single Repo to JSON:")
    print(RepoEncoder().encode(fetcher._repos[0]))
    print("serializing a single Repo to JSON with dumps")
    print(json.dumps(fetcher._repos[0], indent=4, cls=RepoEncoder))
    print("serializing a RepoFetcher to JSON:")
    print(FetcherEncoder().encode(fetcher))
    print("serializing a RepoFetcher to JSON with dumps")
    print(json.dumps(fetcher, indent=4, cls=FetcherEncoder))
"""

def main():
    description = "Manage OE build infrastructure."
    repos_json_help = "A JSON file describing the state of the repos."
    action_help = "An action to perform on the build directory."
    conf_dir_help = "Directory where all local bitbake configs live."
    manifest_help = "Generate JSON manifest describing current state of repos."
    setup_help = "Setup the OE build directory. This includes cloning the " \
            "repos from the JSON file and creating the bblayers.conf " \
            "file."
    source_dir_help = "Checkout git repos into this directory."

    parser = argparse.ArgumentParser(prog=__file__, description=description)
    actionparser = parser.add_subparsers(help=action_help)
    # parser for 'setup' action
    setup_parser = actionparser.add_parser("setup", help=setup_help)
    setup_parser.add_argument("-c", "--conf-dir", default="conf", help=conf_dir_help)
    setup_parser.add_argument("-r", "--repos-json", default="LAYERS.json", help=repos_json_help)
    setup_parser.add_argument("-s", "--src-dir", default="source", help=source_dir_help)
    setup_parser.set_defaults(func=setup)
    # parser for 'manifest' action
    manifest_parser = actionparser.add_parser("manifest", help=manifest_help)
    manifest_parser.add_argument("-r", "--repos-json", default=sys.stdout, help=repos_json_help)
    manifest_parser.add_argument("-s", "--src-dir", default="source", help=source_dir_help)
    manifest_parser.set_defaults(func=manifest)

    args = parser.parse_args()
    args.func(args)

    return 

if __name__ == '__main__':
    main()

