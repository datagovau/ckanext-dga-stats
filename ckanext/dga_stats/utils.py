# -*- coding: utf-8 -*-

from __future__ import absolute_import
from builtins import str
import time
import logging

import ckan.lib.helpers as h
import ckan.plugins as p

from . import stats as stats_lib

log = logging.getLogger(__name__)

def _timed(f, arg=None):
    start = time.time()
    if arg:
        ret = f(arg)
    else:
        ret = f()
    elapsed = time.time() - start
    log.info(f.__name__ + " " + str(elapsed) + ' seconds')
    return ret


def index():
    extra_vars = {}
    stats = stats_lib.Stats()
    rev_stats = stats_lib.RevisionStats()
    extra_vars["top_rated_packages"] = _timed(stats.top_rated_packages)
    extra_vars["most_edited_packages"] = _timed(stats.most_edited_packages)
    extra_vars["largest_groups"] = _timed(stats.largest_groups)
    extra_vars["top_package_owners"] = _timed(stats.top_package_owners)
    extra_vars["summary_stats"] = _timed(stats.summary_stats)
    extra_vars["activity_counts"] = _timed(stats.activity_counts)
    extra_vars["by_org"] = _timed(stats.by_org)
    extra_vars["users_by_organisation"] = _timed(stats.users_by_organisation)
    extra_vars["res_by_org"] = _timed(stats.res_by_org)
    extra_vars["top_active_orgs"] = _timed(stats.top_active_orgs)
    extra_vars["user_access_list"] = _timed(stats.user_access_list)
    extra_vars["recent_created_datasets"] = _timed(stats.recent_created_datasets)
    extra_vars["recent_updated_datasets"] = _timed(stats.recent_updated_datasets)
    extra_vars["new_packages_by_week"] = _timed(rev_stats.get_by_week, 'new_packages')
    extra_vars["num_packages_by_week"] = _timed(rev_stats.get_num_packages_by_week)
    extra_vars["package_revisions_by_week"] = _timed(rev_stats.get_by_week,
                                         'package_revisions')
    extra_vars["recent_period"] = stats.recent_period

    # Used in the legacy CKAN templates.
    extra_vars["packages_by_week"] = []

    # Used in new CKAN templates gives more control to the templates for formatting.
    extra_vars["raw_packages_by_week"] = []
    for week_date, num_packages, cumulative_num_packages in extra_vars["num_packages_by_week"]:
        extra_vars["packages_by_week"].append(
            '[new Date(%s), %s]' %
            (week_date.replace('-', ','), cumulative_num_packages))
        extra_vars["raw_packages_by_week"].append({
            'date': h.date_str_to_datetime(week_date),
            'total_packages': cumulative_num_packages
        })

    extra_vars["all_package_revisions"] = []
    extra_vars["raw_all_package_revisions"] = []
    for week_date, revs, num_revisions, cumulative_num_revisions in extra_vars["package_revisions_by_week"]:
        extra_vars["all_package_revisions"].append(
            '[new Date(%s), %s]' %
            (week_date.replace('-', ','), num_revisions))
        extra_vars["raw_all_package_revisions"].append({
            'date':
            h.date_str_to_datetime(week_date),
            'total_revisions':
            num_revisions
        })

    extra_vars["new_datasets"] = []
    extra_vars["raw_new_datasets"] = []
    for week_date, pkgs, num_packages, cumulative_num_packages in extra_vars["new_packages_by_week"]:
        extra_vars["new_datasets"].append('[new Date(%s), %s]' %
                              (week_date.replace('-', ','), num_packages))
        extra_vars["raw_new_datasets"].append({
            'date': h.date_str_to_datetime(week_date),
            'new_packages': num_packages
        })

    return p.toolkit.render('ckanext/stats/index.html', extra_vars)
