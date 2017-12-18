
from __future__ import unicode_literals

import logging
import importlib
import datetime
from collections import defaultdict

import pandas as pd
import numpy as np
import networkx as nx

from common import decorators as d
from common import email
import scraper

logger = logging.getLogger("ghd")
fs_cache = d.fs_cache('common')

SUPPORTED_ECOSYSTEMS = ('npm', 'pypi')

SUPPORTED_METRICS = {
    'commits': scraper.commit_stats,
    # 'contributors': scraper.commit_users,
    'gini': scraper.commit_gini,
    'q50': lambda repo: scraper.contributions_quantile(repo, 0.5),
    'q70': lambda repo: scraper.contributions_quantile(repo, 0.7),
    'q90': lambda repo: scraper.contributions_quantile(repo, 0.9),
    'issues': scraper.new_issues,
    'closed_issues': scraper.closed_issues,
    'non_dev_issues': scraper.non_dev_issue_stats,
    'submitters': scraper.submitters,
    'non_dev_submitters': scraper.non_dev_submitters,
    'commercial': scraper.commercial_involvement,
    'university': scraper.university_involvement,
}


def _get_ecosystem(ecosystem):
    """Returns an imported module for the ecosystem.
    Basically, an importlib wrapper
    :param ecosystem: str:{pypi|npm}
    :return: module
    """
    assert ecosystem in SUPPORTED_ECOSYSTEMS, "Ecosystem is not supported"
    return importlib.import_module(ecosystem)


@fs_cache
def package_urls(ecosystem):
    # type: (str) -> pd.DataFrame
    """Get list of packages and their respective GitHub repositories"""
    es = _get_ecosystem(ecosystem)
    return es.package_urls().dropna().rename("github_url")


@fs_cache
def package_owners(ecosystem):
    es = _get_ecosystem(ecosystem)
    return es.package_owners().dropna().rename('owner')


@fs_cache
def first_contrib_dates(ecosystem):
    # type: (str) -> pd.Series
    # ~100 without caching
    return pd.Series({package: scraper.commits(url)['authored_date'].min()
                      for package, url in package_urls(ecosystem).iteritems()})


@fs_cache
def monthly_data(ecosystem, metric):
    # type: (str, str) -> pd.DataFrame
    """
    :param ecosystem: str
    :param metric: str:
    :return: pd.DataFrame
    """
    # providers are expected to accept package github url
    # and return a single column dataframe
    assert metric in SUPPORTED_METRICS, "Metric is not supported"
    metric_provider = SUPPORTED_METRICS[metric]

    def gen():
        for package, url in package_urls(ecosystem).iteritems():
            logger.info("Processing %s", package)
            yield metric_provider(url).rename(package)

    return pd.DataFrame(gen())


def contributors(ecosystem, months=1):
    # type: (str) -> pd.DataFrame
    assert months > 0
    """ Get a historical list of developers contributing to ecosystem projects
    This function takes 7m20s for 54k PyPi projects @months=1, 23m20s@4
    :param ecosystem: {"pypi"|"npm"}
    :return: pd.DataFrame, index is projects, columns are months, cells are
        sets of stirng github usernames
    """
    fname = fs_cache.get_cache_fname("contributors", ecosystem, months)
    if fs_cache.expired(fname):
        # fcd = first_contrib_dates(ecosystem).dropna()
        start = scraper.MIN_DATE
        columns = [d.strftime("%Y-%m")
                   for d in pd.date_range(start, 'now', freq="M")][:-3]

        def gen():
            for package, repo in package_urls(ecosystem).iteritems():
                logger.info("Processing %s: %s", package, repo)
                s = scraper.commit_user_stats(repo).reset_index()[
                    ['authored_date', 'author']].groupby('authored_date').agg(
                    lambda df: set(df['author']))['author'].rename(
                    package).reindex(columns)
                if months > 1:
                    s = pd.Series(
                        (set().union(*[c for c in s[max(0, i-months+1):i+1]
                                     if c and pd.notnull(c)])
                         for i in range(len(columns))),
                        index=columns, name=package)
                yield s

        df = pd.DataFrame(gen(), columns=columns)

        # transform and write the dataframe
        df.applymap(
            lambda s: ",".join(str(u) for u in s) if s and pd.notnull(s) else ""
        ).to_csv(fname)

        return df

    df = pd.read_csv(fname, index_col=0, dtype=str)
    return df.applymap(
        lambda s: set(s.split(",")) if s and pd.notnull(s) else set())


@fs_cache
def active_contributors(ecosystem, months=1):
    return count_dependencies(contributors(ecosystem, months))


@fs_cache
def connectivity(ecosystem, months=1000):
    # type: (str, int) -> pd.DataFrame
    """ Number of projects focal project is connected to via its developers

    :param ecosystem: {"pypi"|"npm"}
    :param months: number of months to lookbehind for shared contributors
    :type ecosystem: str
    :type months: int
    :return: pd.DataFrame, index is projects, columns are months
    :rtype months: pd.DataFrame
    """
    # "-" stands for anonymous user
    cs = contributors(ecosystem, months).applymap(
        lambda x: x.difference(["-"]) if pd.notnull(x) else x)
    owners = package_urls(ecosystem).map(lambda x: x.split("/", 1)[0])

    def gen():
        for month, row in cs.T.iterrows():
            logger.info("Processing %s", month)
            conn = []

            projects = defaultdict(set)
            for project, users in row.iteritems():
                for user in users:
                    projects[user].add(project)

            for project, users in row.iteritems():
                ps = set().union(*[projects[user] for user in users])
                conn.append(sum(owners[p] != owners[project] for p in ps))

            yield pd.Series(conn, index=row.index, name=month)

    return pd.DataFrame(gen(), columns=cs.index).T


@fs_cache
def account_data(ecosystem):
    urls = package_urls(ecosystem)
    users = set(repo_url.split("/", 1)[0].lower() for repo_url in urls)
    api = scraper.GitHubAPI()

    def gen():
        for user in users:
            try:
                yield api.user_info(user)
            except scraper.RepoDoesNotExist:
                continue

    df = pd.DataFrame(
        gen(), columns=['id', 'login', 'org', 'type', 'public_repos',
                        'followers', 'following', 'created_at', 'updated_at'])
    df['org'] = df['type'].map({"Organization": True, "User": False})

    return df.drop('type', 1).set_index('login')


def upstreams(ecosystem):
    # type: (str) -> pd.DataFrame
    # ~12s without caching
    es = _get_ecosystem(ecosystem)
    deps = es.deps_and_size().sort_values("date")
    deps['dependencies'] = deps['dependencies'].map(
        lambda x: set(x.split(",")) if x and pd.notnull(x) else set())

    idx = [d.strftime("%Y-%m")  # start is around 2005
           for d in pd.date_range(deps['date'].min(), 'now', freq="M")]

    df = deps.groupby([deps.index, deps['date'].str[:7]])['dependencies'].last()
    return df.unstack(level=-1).T.reindex(idx).fillna(method='ffill').T


def downstreams(uss):
    """ Basically, reversed upstreams
    :param uss: either ecosystem (pypi|npm) or an upstreams DataFrame
    :return: pd.DataFrame, df.loc[project, month] = set([*projects])
    """
    # ~35s without caching
    if isinstance(uss, str):
        uss = upstreams(uss)

    def gen(row):
        s = defaultdict(set)
        for pkg, dss in row.iteritems():
            if dss and pd.notnull(dss):
                # add package as downstream to each of upstreams
                for ds in dss:
                    s[ds].add(pkg)
        return pd.Series(s, name=row.name, index=row.index)

    return uss.apply(gen, axis=0)


def cumulative_dependencies(deps):
    # apply - 150s
    # owners = package_owners("pypi")

    def gen(dependencies):
        cumulative_upstreams = {}

        def traverse(pkg):
            if pkg not in cumulative_upstreams:
                cumulative_upstreams[pkg] = set()  # prevent infinite loop
                ds = dependencies[pkg]
                if ds and pd.notnull(ds):
                    cumulative_upstreams[pkg] = set.union(
                        ds, *(traverse(d) for d in ds if d in dependencies))
            return cumulative_upstreams[pkg]

        return pd.Series(dependencies.index, index=dependencies.index).map(
            traverse).rename(dependencies.name)

    return deps.apply(gen, axis=0)


def count_dependencies(df):
    # type: (pd.DataFrame) -> pd.DataFrame
    # takes around 20s for full pypi history
    return df.applymap(lambda s: len(s) if s and pd.notnull(s) else 0)


def _fcd(ecosystem, start_date):
    es = _get_ecosystem(ecosystem)
    fcd = first_contrib_dates(ecosystem).dropna().str[:7]
    fcd = fcd[fcd > start_date]
    deps = es.deps_and_size()
    # first_release_date
    frd = deps["date"].groupby("name").min().reindex(fcd.index).fillna("9999")
    # remove packages which were released before first commits
    # usually those are imports from other VCSes
    return fcd[fcd <= frd]  # drops 623 packages


@fs_cache
def dead_projects(ecosystem):
    # definition of dead: <= 1 commit per month on average in a year
    # or, if commits data unavailable, over 1 year since last release
    es = _get_ecosystem(ecosystem)
    deps = es.deps_and_size()
    commits = monthly_data(ecosystem, "commits")
    last_release = deps[['date']].groupby("name").max()
    death_date = pd.to_datetime(last_release['date'], format="%Y-%m-%d") + \
        datetime.timedelta(days=365)
    death_str = death_date.dt.strftime("%Y-%m-%d")

    dead = pd.DataFrame([(death_str <= month).rename(month)
                         for month in commits.columns]).T
    sure_dead = (commits.T[::-1].rolling(
                 window=12, min_periods=1).max() <= 1)[::-1].T.astype(bool)
    dead.update(sure_dead)
    return dead


# TODO:
# network centrality dependencies
# network centrality contributors

def _count_deps(deps, ecosystem, start_date, active_only, transitive):
    dead = dead_projects(ecosystem).loc[:, start_date:]
    deps = deps.loc[dead.index, dead.columns]
    if active_only:
        deps = deps.where(~dead)
    if transitive:
        deps = cumulative_dependencies(deps)
    return count_dependencies(deps)


@fs_cache
def count_downstreams(ecosystem, start_date, active_only=False, transitive=False):
    return _count_deps(
        downstreams(ecosystem), ecosystem, start_date, active_only, transitive)


@fs_cache
def count_upstreams(ecosystem, start_date, active_only, transitive):
    return _count_deps(
        upstreams(ecosystem), ecosystem, start_date, active_only, transitive)


@fs_cache
def new_downstreams(ecosystem, start_date, active_only, transitive):
    """" an attempt to not count repeating owner/org combinations in downstreams
        did not work = DELETE
    """
    dead = dead_projects(ecosystem).loc[:, start_date:]
    deps = downstreams(ecosystem).loc[dead.index, dead.columns]
    if active_only:
        deps = deps.where(~dead)
    if transitive:
        deps = cumulative_dependencies(deps)
    owners = package_owners(ecosystem).to_dict()
    orgs = package_urls(ecosystem).map(lambda x: x.split("/", 1)[0]).to_dict()
    deps = deps.applymap(
        lambda x: set((orgs.get(p, ""), owners.get(p, "")) for p in x) if x and pd.notnull(x) else None)
    return count_dependencies(deps)


def nx_graph(connections):
    """
    :param connections: pd.Dataframe, where columns are months and rows are
            packages. Cells contain

    :return:
    """
    pass


def centrality(how, graph, *args, **kwargs):
    # type: (str, nx.Graph) -> dict
    if not how.endswith("_centrality") and how not in \
            ('communicability', 'communicability_exp', 'estrada_index',
             'communicability_centrality_exp', "subgraph_centrality_exp",
             'dispersion', 'betweenness_centrality_subset', 'edge_load'):
        how += "_centrality"
    assert hasattr(nx, how), "Unknown centrality measure: " + how
    return getattr(nx, how)(graph, *args, **kwargs)


@fs_cache
def dependencies_centrality(ecosystem, start_date, centrality_type):
    """
    [edge_]current_flow_closeness is not defined for digraphs
    current_flow_betweenness - didn't try
    communicability*
    estrada_index
    """
    uss = upstreams(ecosystem).loc[:, start_date:]

    def gen(stub):
        # stub = uss column
        logger.info("Processing %s", stub.name)
        g = nx.DiGraph()
        for pkg, us in stub.iteritems():
            if not us or pd.isnull(us):
                continue
            for u in us:  # u is upstream name
                g.add_edge(pkg, u)

        return pd.Series(centrality(centrality_type, g), index=stub.index)

    return uss.apply(gen, axis=0).fillna(0)


@fs_cache
def contributors_centrality(ecosystem, start_date, centrality_type, months, *args):
    """
    {in|out}_degree are not supported
    eigenvector|katz - didn't converge (increase number of iterations?)
    current_flow_* - requires connected graph
    betweenness_subset* - requires sources
    communicability - doesn't work, internal error
    subgraph - unknown (update nx?)
    local_reaching - requires v

    """
    contras = contributors(ecosystem, months).loc[:, start_date:]
    # {in|out}_degree is not defined for undirected graphs

    def gen(stub):
        logger.info("Processing %s", stub.name)
        projects = defaultdict(set)  # projects[contributor] = set(projects)

        for pkg, cs in stub.iteritems():
            if not cs or pd.isnull(cs):
                continue
            for c in cs:
                projects[c].add(pkg)

        projects["-"] = set()
        g = nx.Graph()

        for pkg, cs in stub.iteritems():
            for c in cs:
                for p in projects[c]:
                    if p != pkg:
                        g.add_edge(pkg, p)
        return pd.Series(centrality(centrality_type, g, *args),
                         index=stub.index)

    return contras.apply(gen, axis=0).fillna(0)


@fs_cache
def monthly_dataset(ecosystem, start_date='2008'):
    # TODO: more descriptive name to distinguish from monthly_data
    fcd = _fcd(ecosystem, start_date)
    mddfs = {metric: monthly_data(ecosystem, metric).loc[:, start_date:]
             for metric in ("commits", "contributors", "gini", "q50", "q70",
                            "issues", "closed_issues", "submitters",
                            "non_dev_submitters", "non_dev_issues", "q90",
                            "commercial", "university")}

    mddfs['dead'] = dead_projects(ecosystem).loc[:, start_date:]

    # TODO: to be replaced by centrality
    logger.info("Connectivity..")
    mddfs['connectivity1'] = connectivity(ecosystem, 1)
    mddfs['connectivity3'] = connectivity(ecosystem, 3)
    mddfs['connectivity6'] = connectivity(ecosystem, 6)
    mddfs['connectivity12'] = connectivity(ecosystem, 12)
    mddfs['connectivity1000'] = connectivity(ecosystem, 1000)

    logger.info("Contributors..")
    mddfs['contributors1'] = active_contributors(ecosystem, 1)
    mddfs['contributors3'] = active_contributors(ecosystem, 3)
    mddfs['contributors6'] = active_contributors(ecosystem, 6)
    mddfs['contributors12'] = active_contributors(ecosystem, 12)

    # TODO: to be replaced by count_X
    logger.info("Dependencies..")
    mddfs['upstreams'] = count_upstreams(ecosystem, start_date, False, False)
    mddfs['c_upstreams'] = count_upstreams(ecosystem, start_date, False, True)
    mddfs['a_upstreams'] = count_upstreams(ecosystem, start_date, True, False)
    mddfs['ac_upstreams'] = count_upstreams(ecosystem, start_date, True, True)

    mddfs['downstreams'] = count_downstreams(ecosystem, start_date, False, False)
    mddfs['c_downstreams'] = count_downstreams(ecosystem, start_date, False, True)
    mddfs['a_downstreams'] = count_downstreams(ecosystem, start_date, True, False)
    mddfs['ac_downstreams'] = count_downstreams(ecosystem, start_date, True, True)

    mddfs['ndownstreams'] = new_downstreams(ecosystem, start_date, False, False)
    mddfs['nc_downstreams'] = new_downstreams(ecosystem, start_date, False, True)
    mddfs['na_downstreams'] = new_downstreams(ecosystem, start_date, True, False)
    mddfs['nac_downstreams'] = new_downstreams(ecosystem, start_date, True, True)

    logger.info("Dependencies centrality...")
    for ctype in('degree', 'in_degree', 'out_degree', 'katz', 'load', 'closeness', 'dispersion'):
        mddfs['dc_'+ctype] = dependencies_centrality("pypi", "2008", ctype)

    logger.info("Contributors centrality...")
    m = 1
    for ctype in('betweenness', "closeness", "degree", "edge_betweenness",
                 "edge_load", "estrada_index", "global_reaching", "harmonic",
                 "load", "subgraph", "subgraph_centrality_exp"):
        mddfs['cc_%s_%s'%(ctype, m)] = contributors_centrality(
            "pypi", "2008", ctype, m)
    m = 3
    for ctype in("closeness", "degree"):
        mddfs['cc_%s_%s'%(ctype, m)] = contributors_centrality(
            "pypi", "2008", ctype, m)

    logger.info("Constructing dataframe..")

    def gen():
        for package, start in fcd.iteritems():
            logger.info("Processing %s", package)
            idx = mddfs["commits"].loc[package, start:].index
            df = pd.DataFrame({
                'project': package,
                'date': idx,
                'age': np.arange(len(idx))
            })
            for metric, mddf in mddfs.items():
                if package in mddf.index:
                    df[metric] = mddf.loc[package, idx].fillna(0).values
                else:  # upstream/downstream for packages without releases
                    df[metric] = 0
            for _, row in df.iterrows():
                yield row

    return pd.DataFrame(gen()).reset_index(drop=True)


def survival_data(ecosystem, start_date="2008"):
    # ~7 seconds for cached md
    md = monthly_dataset(ecosystem, start_date)
    md['dead'] = (md['dead'] == "True")

    window = 12
    max_age = md[["project", "age"]].groupby('project').max()["age"].rename(
        "max_age") - window
    md['max_age'] = md["project"].map(max_age)
    md["dead"] = md["dead"].shift(-1).fillna(method='ffill').astype(bool)
    md = md.loc[md["age"] <= md["max_age"]]

    death = md[["project", "age"]].loc[md["dead"]].groupby('project').min()[
        "age"].rename("death")
    md['death'] = md["project"].map(death)

    sd = md.loc[
        ((md["age"] == md["max_age"]) & pd.isnull(md["death"])) |
        (md["age"] == md["death"]) |
        ((md["age"] == 11) & ((md["death"] > 11) | pd.isnull(md["death"])))
        ].copy()
    ad = account_data("pypi")
    ad.index = ad.index.str.lower()

    urls = package_urls("pypi")
    logins = urls.map(lambda s: s.split("/", 1)[0].lower())

    sd['org'] = sd['project'].map(logins).map(ad['org'])
    sd = sd.loc[pd.notnull(
        sd['org'])]  # will drop 5500 rows /662 projects (deleted accounts)
    sd['org'] = sd['org'].astype(
        int)  # bool - is it an organization or personal account

    sd['d_upstreams0'] = (sd['upstreams'] - sd['a_upstreams'] > 0).astype(int)
    sd["dead"] = sd["dead"].astype(int)

    sd['zero'] = 0
    sd['connectivity1'] = sd[['connectivity1', 'zero']].max(axis=1)
    sd['connectivity3'] = sd[['connectivity3', 'zero']].max(axis=1)
    sd['connectivity6'] = sd[['connectivity6', 'zero']].max(axis=1)

    return sd.drop(columns=[
        'ac_downstreams', 'ac_upstreams', 'c_downstreams', 'c_upstreams',
        'cc_betweenness_1', 'cc_degree_1', 'cc_degree_3',
        'cc_edge_betweenness_1', 'cc_edge_load_1', 'cc_global_reaching_1',
        'cc_harmonic_1', 'cc_load_1', 'cc_subgraph_1',
        'cc_subgraph_centrality_exp_1',
        'connectivity1', 'connectivity12', 'connectivity3', 'connectivity6',
        'contributors12', 'contributors3', 'contributors6',
        'dc_closeness', 'dc_degree', 'dc_dispersion', 'dc_in_degree', 'dc_load',
        'dc_out_degree',
        'death', 'max_age', 'zero',
        'na_downstreams', 'nac_downstreams', 'nc_downstreams', 'ndownstreams'
    ])
