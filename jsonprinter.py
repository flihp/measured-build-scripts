#!/usr/bin/env python

from __future__ import print_function
import json
import sys

class BBLayerSerializer:
    def __init__(self, base, repos=[]):
        self._base = base
        self._repos = repos
    def add_repo(self, repo):
        self._repos.append(repo)
    def write(self, fd=sys.stdout):
        fd.write("LCONF_VERSION = \"5\"\n")
        fd.write("BBPATH = \"${TOPDIR}\"\n")
        fd.write("BBLAYERS = \" \\\n")
        for repo in self._repos:
            if repo._layers is not None:
                for layer in repo._layers:
                    fd.write("    ${{TOPDIR}}/{0}/{1}/{2} \\\n".format(self._base, repo._name, layer))
        fd.write("\"\n")

class RepoFetcher:
    def __init__(self, base, repos=[]):
        self._base = base
        self._repos = repos
    def add_repo(self, repo):
        self._repos.append(repo)
    def __str__(self):
        return ''.join(str(repo) for repo in self._repos)
    def checkout(self):
        raise NotImplementedError

class LayerRepo:
    def __init__(self, name, url, branch="master", revision="head", layers=["./"]):
        self._name = name
        self._url = url
        self._branch = branch
        self._revision = revision
        self._layers = layers
    def set_branch(self, branch):
        self._branch = branch
    def set_revision(self, revision):
        self._revision = revision
    def set_layers(self, layers):
        self._layers = layers
    def __str__(self):
        return ("name:     {0}\n"
                "url:      {1}\n"
                "branch:   {2}\n"
                "revision: {3}\n"
                "layers:   {4}\n".format(self._name, self._url, self._branch,
                                         self._revision,self._layers))

def main():
    fetcher = RepoFetcher("./metas")

    with open('LAYERS.json', 'r') as json_data:
        data = json.load(json_data)
        for repo in data:
            fetcher.add_repo(LayerRepo(repo["name"],
                                       repo["url"],
                                       repo.get("branch","master"),
                                       repo.get("revision", "HEAD"),
                                       repo.get("layers", ["./"])))

    print(fetcher, end='')
    bblayers = BBLayerSerializer("./metas", repos=fetcher._repos)
    with open('bblayers.conf', 'w') as test_file:
        bblayers.write(fd=test_file)

if __name__ == '__main__':
    main()
