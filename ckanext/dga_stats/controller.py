import ckan.plugins as p
from ckan.lib.base import BaseController, config
import stats as stats_lib
import ckan.lib.helpers as h
import time
from logging import getLogger



log = getLogger(__name__)
class StatsController(BaseController):
    def timed(self, f, arg = None):
        start = time.time()
        if arg:
            ret = f(arg)
        else:
            ret = f()
        elapsed = time.time() - start
        log.info(f.__name__ +" "+ str(elapsed) + ' seconds')
        return ret

    def index(self):
        c = p.toolkit.c
        stats = stats_lib.Stats()
        rev_stats = stats_lib.RevisionStats()
        c.top_rated_packages = self.timed(stats.top_rated_packages)
        c.most_edited_packages = self.timed(stats.most_edited_packages)
        c.largest_groups = self.timed(stats.largest_groups)
        c.top_package_owners = self.timed(stats.top_package_owners)
        c.summary_stats = self.timed(stats.summary_stats)
        c.activity_counts = self.timed(stats.activity_counts)
        c.by_org = self.timed(stats.by_org)
        c.users_by_organisation = self.timed(stats.users_by_organisation)
        c.res_by_org = self.timed(stats.res_by_org)
        c.top_active_orgs = self.timed(stats.top_active_orgs)
        c.user_access_list = self.timed(stats.user_access_list)
        c.recent_created_datasets = self.timed(stats.recent_created_datasets)
        c.recent_updated_datasets = self.timed(stats.recent_updated_datasets)
        c.new_packages_by_week = self.timed(rev_stats.get_by_week,'new_packages')
        c.num_packages_by_week = self.timed(rev_stats.get_num_packages_by_week)
        c.package_revisions_by_week = self.timed(rev_stats.get_by_week,'package_revisions')
        c.recent_period = stats.recent_period

        # Used in the legacy CKAN templates.
        c.packages_by_week = []

        # Used in new CKAN templates gives more control to the templates for formatting.
        c.raw_packages_by_week = []
        for week_date, num_packages, cumulative_num_packages in c.num_packages_by_week:
            c.packages_by_week.append('[new Date(%s), %s]' % (week_date.replace('-', ','), cumulative_num_packages))
            c.raw_packages_by_week.append({'date': h.date_str_to_datetime(week_date), 'total_packages': cumulative_num_packages})

        c.all_package_revisions = []
        c.raw_all_package_revisions = []
        for week_date, revs, num_revisions, cumulative_num_revisions in c.package_revisions_by_week:
            c.all_package_revisions.append('[new Date(%s), %s]' % (week_date.replace('-', ','), num_revisions))
            c.raw_all_package_revisions.append({'date': h.date_str_to_datetime(week_date), 'total_revisions': num_revisions})

        c.new_datasets = []
        c.raw_new_datasets = []
        for week_date, pkgs, num_packages, cumulative_num_packages in c.new_packages_by_week:
            c.new_datasets.append('[new Date(%s), %s]' % (week_date.replace('-', ','), num_packages))
            c.raw_new_datasets.append({'date': h.date_str_to_datetime(week_date), 'new_packages': num_packages})

        return p.toolkit.render('ckanext/stats/index.html')

    def leaderboard(self, id=None):
        c = p.toolkit.c
        c.solr_core_url = config.get('ckanext.stats.solr_core_url',
                'http://solr.okfn.org/solr/ckan')
        return p.toolkit.render('ckanext/stats/leaderboard.html')

