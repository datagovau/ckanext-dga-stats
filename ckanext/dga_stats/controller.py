# -*- coding: utf-8 -*-

from ckan.lib.base import BaseController

import ckanext.dga_stats.utils as utils


class StatsController(BaseController):
    def index(self):
        return utils.index()
