# -*- coding: utf-8 -*-

from flask import Blueprint

import ckanext.dga_stats.utils as utils

stats = Blueprint(u'stats', __name__)


def index():
    return utils.index()


stats.add_url_rule(u'/stats', view_func=index)


def get_blueprints():
    return [stats]
