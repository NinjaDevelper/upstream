#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import requests
from requests_toolbelt import MultipartEncoder

from upstream.chunk import Chunk
from upstream.exc import FileError, ResponseError, ConnectError

try:
    from urllib import urlretrieve
except ImportError:
    from urllib.request import urlretrieve
try:
    from urllib2 import urlopen, URLError
except ImportError:
    from urllib.retrieve import urlopen, URLError


class Streamer(object):

    def __init__(self, server):
        """ For uploading and downloading files from Metadisk.

        :param server: URL to the Metadisk server
        """
        self.server = server
        self.check_connectivity()

    def check_connectivity(self):
        """
        Check to see if we even get a connection to the server.
        https://stackoverflow.com/questions/3764291/checking-network-connection

        """
        try:
            urlopen(self.server, timeout=1)
        except URLError:
            raise ConnectError("Could not connect to server.")

    def upload(self, filepath):
        """ Uploads a chunk via POST to the specified node
        to the web-core API.  See API docs:
        https://github.com/Storj/web-core#api-documentation

        :param filepath: Path to file as a string
        :return: upstream.chunk.Chunk
        :raise LookupError: IF
        """
        # Open the file and upload it via POST
        url = self.server + "/api/upload"  # web-core API
        # This is a Transfer-Encoding: chunked filechunk generator
        # that's disabled for fun, also cuz broken APO
        # r = requests.post(url, data=self.filestream(path))
        m = MultipartEncoder(
            {
                'file': ('testfile', open('one-meg.testfile', 'rb'))
            }
        )
        r = requests.post(url, data=m, headers={'Content-Type': m.content_type})

        # Make sure that the API call is actually there
        if r.status_code == 404:
            raise LookupError("API call not found.")
        elif r.status_code == 402:
            raise LookupError("Payment required.")
        elif r.status_code == 500:
            raise LookupError("Server error.")
        elif r.status_code == 201:
            # Everthing checked out, return result
            # based on the format selected
            return Chunk().load_json(r.text)
        else:
            raise LookupError("Received status code %s %s "
                              % (r.status_code, r.reason))


    def _download_chunk(self, chunk, destination=""):
        """ Download a chunk via GET from the specified node.
        https://github.com/storj/web-core

        :param chunk: Information about the chunk to download.
        :param destination: Path where we store the file.
        """

        # Generate request URL
        if chunk.decryptkey == "":
            url = self.server + "/api/download/" + chunk.filehash
        else:
            url = self.server + "/api/download/" + chunk.get_uri()

        # Retrieve chunk from the server and pass it the default file directory
        # or override it to a particular place
        if destination == "":
            return urlretrieve(url, "files/" + chunk.filehash)
        else:
            return urlretrieve(url, destination)

    def _filestream(self, filepath):
        """ Streaming file generator

        :param filepath: Path to file to stream
        :raise FileError: If path is not valid
        """
        expandedpath = os.path.expanduser(filepath)
        try:
            os.path.isfile(expandedpath)
        except AssertionError:
            raise FileError("%s not a file or not found" % filepath)

        with open(expandedpath) as f:
            while True:
                chunk = f.read(self.chunk_size)
                if not chunk:
                    break
                yield chunk
