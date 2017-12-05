
import os

import pandas as pd

from common import decorators as d

fs_cache = d.fs_cache('common')


class InvalidEmail(ValueError):
    pass


def clean(raw_email):
    """Extract email from a full address. Example:
      'John Doe <jdoe+github@foo.com>' -> jdoe@foo.com"""
    if not raw_email or pd.isnull(raw_email):
        return ""
    email = raw_email.split("<", 1)[-1].split(">", 1)[0]
    chunks = email.split("@", 3)
    # git-svn generates emails with several @, e.g.:
    # <rossberg@chromium.org@ce2b1a6d-e550-0410-aec6-3dcde31c8c00>
    if len(chunks) < 2:
        raise InvalidEmail("Invalid email")
    uname = chunks[0].rsplit(" ", 1)[-1]
    addr_domain = chunks[1].split(" ", 1)[0]

    return "%s@%s" % (uname.split("+", 1)[0], addr_domain)


def domain(raw_email):
    # type: (str) -> str
    if not raw_email or pd.isnull(raw_email):
        return ""
    return clean(raw_email).rsplit("@", 1)[-1]


@d.memoize
def university_domains():
    # type: () -> set
    """ Return list of university domains outside of .edu TLD
    NOTE: only 2nd level domain is returned, i.e. for aaa.bbb.uk only bbbl.uk
          will be returned. This is necessary since many universities use
          departmenntal domains, like cs.cmu.edu or andrew.cmu.edu

    How to get the original CSV:
    x = requests.get(
         "https://raw.githubusercontent.com/Hipo/university-domains-list/"
         "master/world_universities_and_domains.json").json()
    domains = set(ds for u in x
                  for ds in u['domains'] if not "edu" in ds.rsplit(".", 2)[-2:])
    domains = list(domains)
    pd.Series(domains, index=domains, name="domain"
    ).drop(
        ["chat.ru"]
    ).to_csv("email_university_domains.csv", index=False)
    """
    fh = open(
        os.path.join(os.path.dirname(__file__), "email_university_domains.csv"))
    return set(addr_domain.strip() for addr_domain in fh)


@d.memoize
def public_domains():
    # type: () -> set
    """ Return list of public email domains (i.e. offering free mailboxes)

    How to get the original CSV:
    x = requests.get(
        "https://gist.githubusercontent.com/tbrianjones/5992856/raw/"
        "87f527af7bdd21997722fa65143a9af7bee92583/"
        "free_email_provider_domains.txt").text.split()
    # manually coded
    x.extend([
        'gmail.com', 'users.noreply.github.com', 'hotmail.com',
        'googlemail.com', 'users.sourceforge.net', 'iki.fi',
        'yahoo.com', 'me.com', 'gmx.de', 'jaraco.com', 'cihar.com',
        'yandex.ru', 'outlook.com', 'gmx.net', 'web.de', 'pobox.com',
        'yahoo.co.uk', 'qq.com', 'free.fr', 'icloud.com', '163.com',
        '50mail.com', 'live.com', 'lavabit.com', 'mail.ru', '126.com',
        'yahoo.fr', 'seznam.cz'
    ])
    domains = list(set(x))  # make it unique
    pd.Series(domains, index=domains, name="domain"
    ).drop(  # mistakenly labeled as public
        ["unican.es"]
    ).to_csv("email_public_domains.csv", index=False)
    """
    fh = open(
        os.path.join(os.path.dirname(__file__), "email_public_domains.csv"))
    return set(addr_domain.strip() for addr_domain in fh)


def is_university(addr, domains=None):
    # type: (str) -> bool
    """ Check if provided email has a university domain

    - either in .edu domain
        (except public sercices like england.edu or australia.edu)
    - or in .edu.TLD (non-US based institutions, like edu.au)
    - or listed in a public list of universities
        since universities often have department addresses as well, only the end
        is matched. E.g. cs.cmu.edu will match cmu.edu

    :param addr: email address
    :param domains: optional, list of university domains
    :return: bool
    """
    if domains is None:
        domains = university_domains()
    chunks = domain(addr).split(".")
    if len(chunks) < 2:
        return False
    return (chunks[-1] == "edu" and chunks[-2] not in ("england", "australia"))\
        or chunks[-2] == "edu" \
        or any(".".join(chunks[i:]) in domains for i in range(len(chunks)-1))


def is_public(addr, domains=None):
    # type: (str) -> bool
    if domains is None:
        domains = public_domains()
    return domain(addr) in domains


def is_university_bulk(addr_series):
    # type: (pd.Series) -> pd.Series
    domains = university_domains()
    return addr_series.map(lambda addr: is_university(addr, domains))


def is_public_bulk(addr_series):
    # type: (pd.Series) -> pd.Series
    domains = public_domains()
    return addr_series.map(lambda addr: is_public(addr, domains))
