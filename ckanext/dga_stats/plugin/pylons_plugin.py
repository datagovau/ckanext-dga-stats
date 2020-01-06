# -*- coding: utf-8 -*-

import ckan.plugins as p


class MixinPlugin(p.SingletonPlugin):
    p.implements(p.IRoutes, inherit=True)

    # IRoutes

    def after_map(self, map):
        map.connect(
            "stats",
            "/stats",
            controller="ckanext.dga_stats.controller:StatsController",
            action="index",
        )
        map.connect(
            "stats_action",
            "/stats/{action}",
            controller="ckanext.dga_stats.controller:StatsController",
        )
        return map
