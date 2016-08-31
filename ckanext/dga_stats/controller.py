import ckan.plugins as p
from ckan.lib.base import BaseController, config
import stats as stats_lib
import ckan.lib.helpers as h

import Queue

class StatsController(BaseController):

    def index(self):
        c = p.toolkit.c
        stats = stats_lib.Stats()
        rev_stats = stats_lib.RevisionStats()
        c.top_rated_packages = stats.top_rated_packages()
        c.most_edited_packages = stats.most_edited_packages()
        c.largest_groups = stats.largest_groups()
        c.top_package_owners = stats.top_package_owners()
        c.summary_stats = stats.summary_stats()
        c.activity_counts = stats.activity_counts()
        c.by_org = stats.by_org()
        c.res_by_org = stats.res_by_org()
        c.top_active_orgs = stats.top_active_orgs()
        c.user_access_list = stats.user_access_list()
        c.recent_datasets = stats.recent_datasets()
        c.new_packages_by_week = rev_stats.get_by_week('new_packages')
        c.num_packages_by_week = rev_stats.get_num_packages_by_week()
        c.package_revisions_by_week = rev_stats.get_by_week('package_revisions')

        # Used in the legacy CKAN templates.
        c.packages_by_week = []

        # Used in new CKAN templates gives more control to the templates for formatting.
        c.raw_packages_by_week = []

        for week_date, num_packages, cumulative_num_packages in c.num_packages_by_week:
            c.packages_by_week.append('[new Date(%s), %s]' % (week_date.replace('-', ','), cumulative_num_packages))
            c.raw_packages_by_week.append({'date': h.date_str_to_datetime(week_date), 'total_packages': cumulative_num_packages})

        c.all_package_revisions = []
        c.raw_all_package_revisions = []
        week_queue = Queue.Queue()
        for week_date, revs, num_revisions, cumulative_num_revisions in c.package_revisions_by_week:
            c.all_package_revisions.append('[new Date(%s), %s]' % (week_date.replace('-', ','), num_revisions))
            c.raw_all_package_revisions.append({'date': h.date_str_to_datetime(week_date), 'total_revisions': num_revisions})
            week_queue.put(week_date)

        c.new_datasets = []
        c.raw_new_datasets = []
        for week_date, pkgs, num_packages, cumulative_num_packages in c.new_packages_by_week:
            revision_week_date = week_queue.get()
            while revision_week_date != week_date:
                c.new_datasets.append('[new Date(%s), %s]' % (revision_week_date.replace('-', ','), 0))
                c.raw_new_datasets.append({'date': h.date_str_to_datetime(revision_week_date), 'new_packages': 0})
                revision_week_date = week_queue.get()

            c.new_datasets.append('[new Date(%s), %s]' % (week_date.replace('-', ','), num_packages))
            c.raw_new_datasets.append({'date': h.date_str_to_datetime(week_date), 'new_packages': num_packages})

        while not week_queue.empty():
            revision_week_date = week_queue.get()
            c.new_datasets.append('[new Date(%s), %s]' % (revision_week_date.replace('-', ','), 0))
            c.raw_new_datasets.append({'date': h.date_str_to_datetime(revision_week_date), 'new_packages': 0})

        return p.toolkit.render('ckanext/stats/index.html')

    def leaderboard(self, id=None):
        c = p.toolkit.c
        c.solr_core_url = config.get('ckanext.stats.solr_core_url',
                'http://solr.okfn.org/solr/ckan')
        return p.toolkit.render('ckanext/stats/leaderboard.html')

