import datetime

from pylons import config
from sqlalchemy import Table, select, func, and_
from sqlalchemy.sql.expression import text

import ckan.plugins as p
import ckan.model as model

import re

cache_enabled = p.toolkit.asbool(config.get('ckanext.stats.cache_enabled', 'True'))

if cache_enabled:
    from pylons import cache

    our_cache = cache.get_cache('stats', type='dbm')

DATE_FORMAT = '%Y-%m-%d'


def table(name):
    return Table(name, model.meta.metadata, autoload=True)


def datetime2date(datetime_):
    return datetime.date(datetime_.year, datetime_.month, datetime_.day)


class Stats(object):
    recent_period = config.get('dga.recent_time_period') or 60
    recent_limit = config.get('dga.recent_page_limit') or 50

    @classmethod
    def top_rated_packages(cls, limit=10):
        # NB Not using sqlalchemy as sqla 0.4 doesn't work using both group_by
        # and apply_avg
        package = table('package')
        rating = table('rating')
        sql = select([package.c.id, func.avg(rating.c.rating), func.count(rating.c.rating)],
                     from_obj=[package.join(rating)]). \
            where(package.c.private == 'f'). \
            group_by(package.c.id). \
            order_by(func.avg(rating.c.rating).desc(), func.count(rating.c.rating).desc()). \
            limit(limit)
        res_ids = model.Session.execute(sql).fetchall()
        res_pkgs = [(model.Session.query(model.Package).get(unicode(pkg_id)), avg, num) for pkg_id, avg, num in res_ids]
        return res_pkgs

    @classmethod
    def most_edited_packages(cls, limit=10):
        package_revision = table('package_revision')
        package = table('package')
        s = select([package_revision.c.id, func.count(package_revision.c.revision_id)],
                   from_obj=[package_revision.join(package)]). \
            where(package.c.private == 'f'). \
            group_by(package_revision.c.id). \
            order_by(func.count(package_revision.c.revision_id).desc()). \
            limit(limit)
        res_ids = model.Session.execute(s).fetchall()
        res_pkgs = [(model.Session.query(model.Package).get(unicode(pkg_id)), val) for pkg_id, val in res_ids]
        return res_pkgs

    @classmethod
    def largest_groups(cls, limit=10):
        member = table('member')
        s = select([member.c.group_id, func.count(member.c.table_id)]). \
            group_by(member.c.group_id). \
            where(member.c.group_id != None). \
            where(member.c.table_name == 'package'). \
            where(member.c.capacity == 'public'). \
            order_by(func.count(member.c.table_id).desc())
        # limit(limit)

        res_ids = model.Session.execute(s).fetchall()
        res_groups = [(model.Session.query(model.Group).get(unicode(group_id)), val) for group_id, val in res_ids]
        return res_groups

    @classmethod
    def by_org(cls, limit=10):
        connection = model.Session.connection()
        res = connection.execute("select package.owner_org, package.private, count(*) from package \
		inner join \"group\" on package.owner_org = \"group\".id \
		where package.state='active'\
		group by package.owner_org,\"group\".name, package.private \
		order by \"group\".name, package.private;").fetchall();
        res_groups = [(model.Session.query(model.Group).get(unicode(group_id)), private, val) for group_id, private, val
                      in res]
        return res_groups

    @classmethod
    def res_by_org(cls, limit=10):
        connection = model.Session.connection()
        reses = connection.execute("select owner_org,format,count(*) from \
		resource inner join package on resource.package_id = package.id group by owner_org,format order by count desc;").fetchall();
        group_ids = []
        group_tab = {}
        group_spatial = {}
        group_other = {}
        for group_id, format, count in reses:
            if group_id not in group_ids:
                group_ids.append(group_id)
                group_tab[group_id] = 0
                group_spatial[group_id] = 0
                group_other[group_id] = 0
            if re.search('xls|csv|ms-excel|spreadsheetml.sheet|zip|netcdf', format, re.IGNORECASE):
                group_tab[group_id] = group_tab[group_id] + count
            elif re.search('wms|wfs|wcs|shp|kml|kmz', format, re.IGNORECASE):
                group_spatial[group_id] = group_spatial[group_id] + count
            else:
                group_other[group_id] = group_other[group_id] + count
        return [(model.Session.query(model.Group).get(unicode(group_id)), group_tab[group_id], group_spatial[group_id],
                 group_other[group_id], group_tab[group_id] + group_spatial[group_id] + group_other[group_id]) for
                group_id in group_ids]

    @classmethod
    def top_active_orgs(cls, limit=10):
        connection = model.Session.connection()
        res = connection.execute("select package.owner_org, count(*) from package \
		inner join \"group\" on package.owner_org = \"group\".id \
                inner join (select distinct object_id from activity where activity.timestamp > (now() - interval '60 day')) \
                latestactivities on latestactivities.object_id = package.id \
                where package.state='active' \
                and package.private = 'f' \
                group by package.owner_org \
                order by count(*) desc;").fetchall();
        res_groups = [(model.Session.query(model.Group).get(unicode(group_id)), val) for group_id, val in res]
        return res_groups

    @classmethod
    def top_package_owners(cls, limit=10):
        package_role = table('package_role')
        user_object_role = table('user_object_role')
        package = table('package')
        s = select([user_object_role.c.user_id, func.count(user_object_role.c.role)], from_obj=[
            user_object_role.join(package_role).join(package, package_role.c.package_id == package.c.id)]). \
            where(user_object_role.c.role == model.authz.Role.ADMIN). \
            where(package.c.private == 'f'). \
            where(user_object_role.c.user_id != None). \
            group_by(user_object_role.c.user_id). \
            order_by(func.count(user_object_role.c.role).desc()). \
            limit(limit)
        res_ids = model.Session.execute(s).fetchall()
        res_users = [(model.Session.query(model.User).get(unicode(user_id)), val) for user_id, val in res_ids]
        return res_users

    @classmethod
    def summary_stats(cls):
        connection = model.Session.connection()

        res = connection.execute("SELECT 'Total Organisations', count(*) from \"group\" where type = 'organization' and state = 'active' union \
				select 'Total Datasets', count(*) from package where package.type='dataset' and package.state='active' and package.private = 'f' and package.id not in (select package_id from package_extra where key = 'harvest_portal') union \
				select 'Total Archived Datasets', count(*) from package where (state='active' or state='draft' or state='draft-complete') and private = 't' and package.id not in (select package_id from package_extra where key = 'harvest_portal') union \
				select 'Total Data Files/Resources', count(*) from resource where resource.state='active' and package_id not IN (select distinct package_id from package INNER JOIN  package_extra on package.id = package_extra.package_id where key = 'harvest_portal') union \
				select 'Total Data API Resources', count(*) from resource where resource.state='active' and (webstore_url = 'active' or format='wms') and package_id not IN (select distinct package_id from package INNER JOIN package_extra on package.id = package_extra.package_id where key = 'harvest_portal')").fetchall();
        return res


    @classmethod
    def activity_counts(cls):
        connection = model.Session.connection()
        res = connection.execute(
            "select to_char(timestamp, 'YYYY-MM') as month,activity_type, count(*) from activity group by month, activity_type order by month;").fetchall();
        return res

    @classmethod
    def users_by_organisation(cls):
        connection = model.Session.connection()
        res = connection.execute(
            "select \"group\".id,\"user\".id ,capacity, sysadmin from \"group\""
            "        inner join member on member.group_id = \"group\".id"
            "        inner join \"user\" on member.table_id = \"user\".id"
            "        where capacity is not null and \"group\".type = 'organization' and member.state='active' order by sysadmin, \"group\".name, capacity;").fetchall()
        result = [(model.Session.query(model.Group).get(unicode(org)), model.Session.query(model.User).get(unicode(user_id)), role, sysadmin ) for
                  (org, user_id, role, sysadmin) in res]
        return result

    @classmethod
    def user_access_list(cls):
        connection = model.Session.connection()
        res = connection.execute(
            "select \"user\".id ,sysadmin,capacity,max(last_active),array_agg(\"group\".name) member_of_orgs from \"user\" "
            " left outer join member on member.table_id = \"user\".id "\
            " left OUTER JOIN (select max(timestamp) last_active,user_id from activity group by user_id) a on \"user\".id = a.user_id "\
            " left outer join \"group\" on member.group_id = \"group\".id  where sysadmin = 't' or (capacity is not null and member.state = 'active')"\
            " group by \"user\".id ,sysadmin,capacity order by max(last_active) desc;").fetchall()
        result = [(model.Session.query(model.User).get(unicode(user_id)), sysadmin, role, last_active, orgs) for
                  (user_id, sysadmin, role, last_active, orgs) in res]
        return result

    @classmethod
    def recent_created_datasets(cls):
        connection = model.Session.connection()
        result = connection.execute("select timestamp,package.id,user_id,maintainer from package "
                                    "inner join (select id, min(revision_timestamp) as timestamp from package_revision group by id) a on a.id=package.id "
                                    "full outer join (select object_id,user_id from activity "
                                    "where activity_type = 'new package' and timestamp > NOW() - interval '{recent_period} day') act on act.object_id=package.id "
                                    "FULL OUTER JOIN (select package_id,key from package_extra "
                                    "where key = 'harvest_portal') e on e.package_id=package.id "
                                    "where key is null and private = 'f' and state='active' "
                                    "and timestamp > NOW() - interval '{recent_period} day' order by timestamp asc LIMIT {recent_limit};".format(
                                        recent_period=cls.recent_period,
                                        recent_limit=cls.recent_limit)).fetchall()
        r = []
        for timestamp, package_id, user_id, maintainer in result:
            package = model.Session.query(model.Package).get(unicode(package_id))
	    if user_id:
		    user = model.Session.query(model.User).get(unicode(user_id))
	    else:
		    user = model.User.by_name(unicode(maintainer))
            if package.owner_org:
                r.append((
                datetime2date(timestamp), package, model.Session.query(model.Group).get(unicode(package.owner_org)),
                user))
            else:
                r.append(
                    (datetime2date(timestamp), package, None,user))
        return r

    @classmethod
    def recent_updated_datasets(cls):
        connection = model.Session.connection()
        result = connection.execute("select timestamp::date,package.id,user_id from package "
                                    "inner join activity on activity.object_id=package.id "
                                    "FULL OUTER JOIN (select package_id,key from package_extra "
                                    "where key = 'harvest_portal') e on e.package_id=package.id "
                                    "where key is null and activity_type = 'changed package' "
                                    "and timestamp > NOW() - interval '{recent_period} day' and private = 'f' and state='active'"
                                    "GROUP BY package.id,user_id,timestamp::date,activity_type "
                                    "order by timestamp::date asc LIMIT {recent_limit};".format(
                                        recent_period=cls.recent_period,
                                        recent_limit=cls.recent_limit)).fetchall()
        r = []
        for timestamp, package_id, user_id in result:
            package = model.Session.query(model.Package).get(unicode(package_id))
            if package.owner_org:
                r.append((timestamp, package, model.Session.query(model.Group).get(unicode(package.owner_org)),
                    model.Session.query(model.User).get(unicode(user_id))))
            else:
                r.append(
                    (timestamp, package, None, model.Session.query(model.User).get(unicode(user_id))))
        return r


class RevisionStats(object):
    @classmethod
    def package_addition_rate(cls, weeks_ago=0):
        week_commenced = cls.get_date_weeks_ago(weeks_ago)
        return cls.get_objects_in_a_week(week_commenced,
                                         type_='package_addition_rate')

    @classmethod
    def package_revision_rate(cls, weeks_ago=0):
        week_commenced = cls.get_date_weeks_ago(weeks_ago)
        return cls.get_objects_in_a_week(week_commenced,
                                         type_='package_revision_rate')

    @classmethod
    def get_date_weeks_ago(cls, weeks_ago):
        '''
        @param weeks_ago: specify how many weeks ago to give count for
                          (0 = this week so far)
        '''
        date_ = datetime.date.today()
        return date_ - datetime.timedelta(days=
                                          datetime.date.weekday(date_) + 7 * weeks_ago)

    @classmethod
    def get_week_dates(cls, weeks_ago):
        '''
        @param weeks_ago: specify how many weeks ago to give count for
                          (0 = this week so far)
        '''
        package_revision = table('package_revision')
        revision = table('revision')
        today = datetime.date.today()
        date_from = datetime.datetime(today.year, today.month, today.day) - \
                    datetime.timedelta(days=datetime.date.weekday(today) + \
                                            7 * weeks_ago)
        date_to = date_from + datetime.timedelta(days=7)
        return (date_from, date_to)

    @classmethod
    def get_date_week_started(cls, date_):
        assert isinstance(date_, datetime.date)
        if isinstance(date_, datetime.datetime):
            date_ = datetime2date(date_)
        return date_ - datetime.timedelta(days=datetime.date.weekday(date_))

    @classmethod
    def get_package_revisions(cls):
        '''
        @return: Returns list of revisions and date of them, in
                 format: [(id, date), ...]
        '''
        package_revision = table('package_revision')
        revision = table('revision')
        s = select([package_revision.c.id, revision.c.timestamp], from_obj=[package_revision.join(revision)]).order_by(
            revision.c.timestamp)
        res = model.Session.execute(s).fetchall()  # [(id, datetime), ...]
        return res

    @classmethod
    def get_new_packages(cls):
        '''
        @return: Returns list of new pkgs and date when they were created, in
                 format: [(id, date_ordinal), ...]
        '''

        def new_packages():
            # Can't filter by time in select because 'min' function has to
            # be 'for all time' else you get first revision in the time period.
            connection = model.Session.connection()
            res = connection.execute(""
                                     "SELECT package_revision.id, min(revision.timestamp) AS min_1 FROM package_revision "
                                     "JOIN revision ON revision.id = package_revision.revision_id "
                                     "WHERE package_revision.id in (select id from package where package.type='dataset' and package.state='active' and package.private = 'f')"
                                     "and package_revision.id not in (select package_id from package_extra where key = 'harvest_portal') "
                                     "GROUP BY package_revision.id ORDER BY min(revision.timestamp)")
            res_pickleable = []
            for pkg_id, created_datetime in res:
                res_pickleable.append((pkg_id, created_datetime.toordinal()))
            return res_pickleable

        if cache_enabled:
            week_commences = cls.get_date_week_started(datetime.date.today())
            key = 'all_new_packages_%s' + week_commences.strftime(DATE_FORMAT)
            new_packages = our_cache.get_value(key=key,
                                               createfunc=new_packages)
        else:
            new_packages = new_packages()
        return new_packages


    @classmethod
    def get_num_packages_by_week(cls):
        def num_packages():
            new_packages_by_week = cls.get_by_week('new_packages')

            first_date = datetime.datetime.strptime(new_packages_by_week[0][0], DATE_FORMAT).date()
            cls._cumulative_num_pkgs = 0
            new_pkgs = []


            def build_weekly_stats(week_commences, new_pkg_ids, deleted_pkg_ids):
                num_pkgs = len(new_pkg_ids)
                new_pkgs.extend([model.Session.query(model.Package).get(id).name for id in new_pkg_ids])

                cls._cumulative_num_pkgs += num_pkgs
                return (week_commences.strftime(DATE_FORMAT),
                        num_pkgs, cls._cumulative_num_pkgs)

            week_ends = first_date
            today = datetime.date.today()
            new_package_week_index = 0
            deleted_package_week_index = 0
            weekly_numbers = []  # [(week_commences, num_packages, cumulative_num_pkgs])]
            while week_ends <= today:
                week_commences = week_ends
                week_ends = week_commences + datetime.timedelta(days=7)
                if datetime.datetime.strptime(new_packages_by_week[new_package_week_index][0],
                                              DATE_FORMAT).date() == week_commences:
                    new_pkg_ids = new_packages_by_week[new_package_week_index][1]
                    new_package_week_index += 1
                else:
                    new_pkg_ids = []

                weekly_numbers.append(build_weekly_stats(week_commences, new_pkg_ids, []))
            # just check we got to the end of each count
            assert new_package_week_index == len(new_packages_by_week)
            return weekly_numbers

        if cache_enabled:
            week_commences = cls.get_date_week_started(datetime.date.today())
            key = 'number_packages_%s' + week_commences.strftime(DATE_FORMAT)
            num_packages = our_cache.get_value(key=key,
                                               createfunc=num_packages)
        else:
            num_packages = num_packages()
        return num_packages

    @classmethod
    def get_by_week(cls, object_type):
        cls._object_type = object_type

        def objects_by_week():
            if cls._object_type == 'new_packages':
                objects = cls.get_new_packages()

                def get_date(object_date):
                    return datetime.date.fromordinal(object_date)
            elif cls._object_type == 'package_revisions':
                objects = cls.get_package_revisions()

                def get_date(object_date):
                    return datetime2date(object_date)
            else:
                raise NotImplementedError()
            first_date = get_date(objects[0][1]) if objects else datetime.date.today()
            week_commences = cls.get_date_week_started(first_date)
            week_ends = week_commences + datetime.timedelta(days=7)
            week_index = 0
            weekly_pkg_ids = []  # [(week_commences, [pkg_id1, pkg_id2, ...])]
            pkg_id_stack = []
            cls._cumulative_num_pkgs = 0

            def build_weekly_stats(week_commences, pkg_ids):
                num_pkgs = len(pkg_ids)
                cls._cumulative_num_pkgs += num_pkgs
                return (week_commences.strftime(DATE_FORMAT),
                        pkg_ids, num_pkgs, cls._cumulative_num_pkgs)

            for pkg_id, date_field in objects:
                date_ = get_date(date_field)
                if date_ >= week_ends:
                    weekly_pkg_ids.append(build_weekly_stats(week_commences, pkg_id_stack))
                    pkg_id_stack = []
                    week_commences = week_ends
                    week_ends = week_commences + datetime.timedelta(days=7)
                pkg_id_stack.append(pkg_id)
            weekly_pkg_ids.append(build_weekly_stats(week_commences, pkg_id_stack))
            today = datetime.date.today()
            while week_ends <= today:
                week_commences = week_ends
                week_ends = week_commences + datetime.timedelta(days=7)
                weekly_pkg_ids.append(build_weekly_stats(week_commences, []))
            return weekly_pkg_ids

        if cache_enabled:
            week_commences = cls.get_date_week_started(datetime.date.today())
            key = '%s_by_week_%s' % (cls._object_type, week_commences.strftime(DATE_FORMAT))
            objects_by_week_ = our_cache.get_value(key=key,
                                                   createfunc=objects_by_week)
        else:
            objects_by_week_ = objects_by_week()
        return objects_by_week_

    @classmethod
    def get_objects_in_a_week(cls, date_week_commences,
                              type_='new-package-rate'):
        '''
        @param type: Specifies what to return about the specified week:
                     "package_addition_rate" number of new packages
                     "package_revision_rate" number of package revisions
                     "new_packages" a list of the packages created
                     in a tuple with the date.
                     "deleted_packages" a list of the packages deleted
                     in a tuple with the date.
        @param dates: date range of interest - a tuple:
                     (start_date, end_date)
        '''
        assert isinstance(date_week_commences, datetime.date)
        if type_ in ('package_addition_rate', 'new_packages'):
            object_type = 'new_packages'
        elif type_ == 'package_revision_rate':
            object_type = 'package_revisions'
        else:
            raise NotImplementedError()
        objects_by_week = cls.get_by_week(object_type)
        date_wc_str = date_week_commences.strftime(DATE_FORMAT)
        object_ids = None
        for objects_in_a_week in objects_by_week:
            if objects_in_a_week[0] == date_wc_str:
                object_ids = objects_in_a_week[1]
                break
        if object_ids is None:
            raise TypeError('Week specified is outside range')
        assert isinstance(object_ids, list)
        if type_ in ('package_revision_rate', 'package_addition_rate'):
            return len(object_ids)
        elif type_ in ('new_packages', 'deleted_packages'):
            return [model.Session.query(model.Package).get(pkg_id) \
                    for pkg_id in object_ids]

