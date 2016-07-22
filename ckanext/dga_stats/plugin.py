from logging import getLogger

log = getLogger(__name__)

import ckan.plugins as p
import datetime as datetime

def date_range():
    return list(reversed(range(2013,datetime.datetime.now().year+1)))

class StatsPlugin(p.SingletonPlugin):
    '''Stats plugin.'''

    p.implements(p.IRoutes, inherit=True)
    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.ITemplateHelpers)

    def get_helpers(self):
        '''Register the most_popular_groups() function above as a template
        helper function.

        '''
        # Template helper function names should begin with the name of the
        # extension they belong to, to avoid clashing with functions from
        # other extensions.
        return {
            'date_range': date_range
        }

    def after_map(self, map):
        map.connect('stats', '/stats',
            controller='ckanext.dga_stats.controller:StatsController',
            action='index')
        map.connect('stats_action', '/stats/{action}',
            controller='ckanext.dga_stats.controller:StatsController')
        return map

    def update_config(self, config):
        templates = 'templates'
        if p.toolkit.asbool(config.get('ckan.legacy_templates', False)):
                templates = 'templates_legacy'
        p.toolkit.add_template_directory(config, templates)
        p.toolkit.add_public_directory(config, 'public')
        p.toolkit.add_resource('public/ckanext/stats', 'ckanext_dga_stats')
