#!/usr/bin/env python

import argparse
import github
import csv


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Scrape GitHub profile information for specified logins. "
                    "List of logins is accepted from input (each login on a "
                    "new line), profiles are output as a CSV file with a "
                    "header row.")
    parser.add_argument('token', nargs="+",
                        help='a GitHub API token')
    parser.add_argument('-i', '--input', default="-", nargs="?",
                        type=argparse.FileType('r'),
                        help='File to use as input, empty or "-" for stdin')
    parser.add_argument('-o', '--output', default="-",
                        type=argparse.FileType('w'),
                        help='Output filename, "-" or skip for stdout')
    args = parser.parse_args()

    tokens = args.token or None
    api = github.GitHubAPI(tokens=tokens)

    writer = None

    for login in args.input:
        data = api.user_info(login.strip())

        if not writer:
            writer = csv.DictWriter(args.output, data.keys())
            writer.writeheader()

        writer.writerow(data)
