# -*- coding: utf-8 -*-

from builtins import range
import ckan.plugins as p
import datetime as datetime
from logging import getLogger

log = getLogger(__name__)

if p.toolkit.check_ckan_version("2.9"):
    from ckanext.dga_stats.plugin.flask_plugin import MixinPlugin
else:
    from ckanext.dga_stats.plugin.pylons_plugin import MixinPlugin


def date_range():
    return list(reversed(list(range(2013, datetime.datetime.now().year + 1))))


class StatsPlugin(MixinPlugin, p.SingletonPlugin):
    """Stats plugin."""

    p.implements(p.IConfigurer, inherit=True)
    p.implements(p.ITemplateHelpers)

    # ITemplateHelpers

    def get_helpers(self):
        """Register the most_popular_groups() function above as a template
        helper function.

        """
        # Template helper function names should begin with the name of the
        # extension they belong to, to avoid clashing with functions from
        # other extensions.
        return {"date_range": date_range}

    # IConfigurer

    def update_config(self, config):
        p.toolkit.add_template_directory(config, "../templates")
        p.toolkit.add_public_directory(config, "../public")
        p.toolkit.add_resource("../public/ckanext/stats", "ckanext_dga_stats")
