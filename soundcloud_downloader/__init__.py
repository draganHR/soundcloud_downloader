#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, division

import re
import os
import sys
import time
import urllib
import string
import logging
import argparse
from datetime import datetime
import ConfigParser

import requests
import requests.packages.urllib3


__version__ = '0.0.1'

logger = logging.getLogger(__name__)

base_url = "https://soundcloud.com"
api_url = "https://api-v2.soundcloud.com"


def load_settings(filename):
    config = ConfigParser.ConfigParser()
    config.readfp(open(filename, 'r'))
    return getattr(config, '_sections')


class TrackError(Exception):
    pass


class TrackExists(TrackError):
    pass


class TrackWithDifferentSizeExists(TrackError):
    pass


class Client(object):

    def __init__(self, client_id, permalink, path):
        self.path = path
        self.client_id = client_id
        self.permalink = permalink
        self.timeout = 60
        self.session = requests.Session()
        self.session.mount("https://", requests.adapters.HTTPAdapter(max_retries=1))
        self.user_id = self._get_user_id()

    def _get_user_id(self):
        response = self.session.get("%s/%s" % (base_url, self.permalink), timeout=self.timeout)
        response.raise_for_status()
        last_script = None
        for match in re.finditer(r"<script[^>]*>(.+?)</script>", response.content):
            last_script = match.group(1)
        return int(re.search(r"soundcloud:users:(\d+)", last_script).group(1))

    def get_tracks(self, latest=False):
        url = "%s/users/%s/tracks" % (api_url, self.user_id)
        offset = 0
        track_count = 0
        while offset is not None:
            logger.debug('Fetching track list, offset: %s', offset)
            params = {
                "client_id": self.client_id,
                "representation": "",
                "limit": 100,
                "offset": offset,
                "linked_partitioning": 1,
            }
            response = self.session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            data = response.json()
            track_count += len(data['collection'])
            for track in data['collection']:
                try:
                    self.get_track(track)
                except TrackExists:
                    if latest:
                        logger.info('Downloaded all latest tracks!')
                        return
                except TrackError, e:
                    logger.warning(e)
            if data['next_href']:
                offset = track['id']
            else:
                offset = None
        logger.info('Total tracks: %s', track_count)

    def get_track(self, track):
        track_id = int(track['id'])
        release_date = datetime.strptime(track['release_date'] or track['created_at'], '%Y-%m-%dT%H:%M:%SZ')
        title = self.sanitize_filename(track['title'])
        filename = "[%s] %s [%d].mp3" % (release_date.strftime('%Y-%m-%d'), title, track_id)
        filepath = os.path.join(self.path, filename)

        logger.info('Downloading "%s"', filename)
        url = track['download_url'] + "?" + urllib.urlencode({"client_id": self.client_id})

        # get headers
        start = time.time()
        response = self.session.get(url, stream=True, timeout=self.timeout)
        response.raise_for_status()
        total_size = int(response.headers.get('content-length'))

        # if file exists, check size
        if os.path.isfile(filepath):
            logger.debug('Skipping "%s"', filename)
            response.close()
            if os.path.getsize(filepath) != total_size:
                raise TrackWithDifferentSizeExists('Unexpected file size for file "%s" (expecting %s)' %
                                                   (filename, total_size))
            else:
                raise TrackExists('Track "%s" already exists' % (filename,))

        # download file
        temp_filepath = os.path.join(self.path, "!track-%d.tmp" % track_id)
        with open(temp_filepath, 'wb') as f:
            dl = 0
            for chunk in response.iter_content(8192):
                dl += len(chunk)
                f.write(chunk)
                done = int(50 * dl / total_size)
                sys.stdout.write("\r[%s%s] %s kbps" % ('=' * done,
                                                       ' ' * (50-done),
                                                       dl // 1024 // (time.time() - start)))
            sys.stdout.write("\r")  # Clean progress line
        logger.debug("Download done: %s", time.time() - start)

        os.rename(temp_filepath, filepath)
        if os.path.getsize(filepath) != total_size:
            raise TrackError('Unexpected file size for file "%s" (expecting %s)' %
                             (filename, total_size))

    @staticmethod
    def sanitize_filename(value):
        valid_chars = "-_.,() " + string.ascii_letters + string.digits
        filename = ''.join(c for c in value if c in valid_chars)
        return filename


def generate_playlist(path):
    filename = "!Playlist.pls"
    logger.debug("Generating playlist: %s", filename)
    playlist = []
    for entry in os.listdir(path):
        if entry.endswith(".mp3"):
            playlist.append(entry)
    playlist.sort()

    with open(os.path.join(path, filename), "w") as f:
        f.write("[playlist]\n")
        for i, entry in enumerate(playlist, 1):
            f.write("File%d=%s\n" % (i, entry))
    logger.info('Done! Total playlist entries: %s', len(playlist))


def setup_logging(verbose):
    if verbose > 3:
        level = logging.DEBUG
    elif verbose > 2:
        level = logging.INFO
    else:
        level = logging.WARNING
    logging.basicConfig(level=level, format='%(message)s')
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)


def main():
    parser = argparse.ArgumentParser(prog='soundcloud-downloader',
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     description=__doc__)
    parser.add_argument('path', type=str)
    parser.add_argument('-l', '--latest', dest='latest', action='store_true',
                        help='Download only latest tracks')
    parser.add_argument('-w', '--no-warnings', dest='no_warnings', action='store_true',
                        help='Disable connection warnings')
    parser.add_argument('--verbose', '-v', action='count')

    args = parser.parse_args()
    setup_logging(args.verbose)

    path = os.path.realpath(args.path)
    if not os.path.isdir(path):
        raise parser.error("Invalid path value")
    config_filename = os.path.join(path, ".soundcloud")
    if not os.path.isfile(config_filename):
        raise parser.error("Config file not found")
    settings = load_settings(config_filename)

    if args.no_warnings:
        requests.packages.urllib3.disable_warnings()

    permalink = settings['main']['permalink']
    client_id = settings['main']['client_id']
    c = Client(client_id=client_id, permalink=permalink, path=path)
    c.get_tracks(latest=args.latest)
    generate_playlist(path)


if __name__ == "__main__":
    main()
