## Description

Download soundcloud tracks to directory

## Configuration

Create an empty directory settings file `.soundcloud`. Settings file must contain SoundCloud permalink and client id.
Example:

    >>> cat ~/example/.soundcloud
    [main]
    client_id = qlg3OtAeSTuMnpybNQO8U0GH2ttRh6Us
    permalink = example

Run soundcloud-downloader command:

    cd ~/example/
    soundcloud-downloader . --latest
