# Copyright 2017 Descartes Labs.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import operator
import os
from functools import partial
from cachetools import TTLCache, cachedmethod
from cachetools.keys import hashkey
from .service import Service
from six import string_types


class Places(Service):
    TIMEOUT = (9.5, 120)
    """Places and statistics service https://iam.descarteslabs.com/service/waldo"""

    def __init__(self, url=None, token=None, maxsize=10, ttl=600):
        """The parent Service class implements authentication and exponential
        backoff/retry. Override the url parameter to use a different instance
        of the backing service.
        """
        if url is None:
            url = os.environ.get("DESCARTESLABS_PLACES_URL", "https://platform-services.descarteslabs.com/waldo/dev")

        Service.__init__(self, url, token)
        self.cache = TTLCache(maxsize, ttl)

    def placetypes(self):
        """Get a list of place types.

        Example::
            >>> import descarteslabs as dl
            >>> dl.places.placetypes()
            ['continent', 'country', 'dependency', 'macroregion', 'region',
                'district', 'mesoregion', 'microregion', 'county']
        """
        r = self.session.get('%s/placetypes' % self.url, timeout=self.TIMEOUT)

        return r.json()

    def random(self, geom='low', placetype=None):
        """Get a random location

        geom: string
            Resolution for the shape [low (default), medium, high]

        return: geojson
        """
        params = {}

        if geom:
            params['geom'] = geom

        if placetype:
            params['placetype'] = placetype

        r = self.session.get('%s/random' % self.url, params=params)

        if r.status_code != 200:
            raise RuntimeError("%s: %s" % (r.status_code, r.text))

        return r.json()

    @cachedmethod(operator.attrgetter('cache'), key=partial(hashkey, 'find'))
    def find(self, path, **kwargs):
        """Find candidate slugs based on full or partial path.

        :param str path: Candidate underscore-separated slug.
        :param placetype: Optional place type for filtering.

        Example::

            >>> import descarteslabs as dl
            >>> from pprint import pprint
            >>> results = dl.places.find('morocco')
            >>> _ = results[0].pop('bbox')
            >>> pprint(results)
            [{'id': 85632693,
              'name': 'Morocco',
              'path': 'continent:africa_country:morocco',
              'placetype': 'country',
              'slug': 'africa_morocco'}]
        """
        r = self.session.get('%s/find/%s' % (self.url, path), params=kwargs, timeout=self.TIMEOUT)

        return r.json()

    @cachedmethod(operator.attrgetter('cache'), key=partial(hashkey, 'shape'))
    def shape(self, slug, output='geojson', geom='low'):
        """Get the geometry for a specific slug

        :param slug: Slug identifier.
        :param str output: Desired geometry format (`GeoJSON`).
        :param str geom: Desired resolution for the geometry (`low`, `medium`, `high`).

        :return: GeoJSON ``Feature``

        Example::
            >>> import descarteslabs as dl
            >>> from pprint import pprint
            >>> kansas = dl.places.shape('north-america_united-states_kansas')
            >>> kansas['bbox']
            [-102.051744, 36.993016, -94.588658, 40.003078]

            >>> kansas['geometry']['type']
            'Polygon'

            >>> pprint(kansas['properties'])
            {'name': 'Kansas',
             'parent_id': 85633793,
             'path': 'continent:north-america_country:united-states_region:kansas',
             'placetype': 'region',
             'slug': 'north-america_united-states_kansas'}

        """
        r = self.session.get('%s/shape/%s.%s' % (self.url, slug, output), params={'geom': geom}, timeout=self.TIMEOUT)

        return r.json()

    @cachedmethod(operator.attrgetter('cache'), key=partial(hashkey, 'prefix'))
    def prefix(self, slug, output='geojson', placetype=None, geom='low'):
        """Get all the places that start with a prefix

        :param str slug: Slug identifier.
        :param str output: Desired geometry format (`GeoJSON`, `TopoJSON`).
        :param str placetype: Restrict results to a particular place type.
        :param str geom: Desired resolution for the geometry (`low`, `medium`, `high`).

        :return: GeoJSON or TopoJSON ``FeatureCollection``

        Example::
            >>> import descarteslabs as dl
            >>> il_counties = dl.places.prefix('north-america_united-states_illinois', placetype='county')
            >>> len(il_counties['features'])
            102

        """
        params = {}
        if placetype:
            params['placetype'] = placetype
        params['geom'] = geom
        r = self.session.get('%s/prefix/%s.%s' % (self.url, slug, output),
                             params=params, timeout=self.TIMEOUT)

        return r.json()

    def sources(self):
        """Get a list of sources
        """
        r = self.session.get('%s/sources' % (self.url), timeout=self.TIMEOUT)

        return r.json()

    def categories(self):
        """Get a list of categories
        """
        r = self.session.get('%s/categories' % (self.url), timeout=self.TIMEOUT)

        return r.json()

    def metrics(self):
        """Get a list of metrics
        """
        r = self.session.get('%s/metrics' % (self.url), timeout=self.TIMEOUT)

        return r.json()

    def data(self, slug, source=None, category=None, metric=None, date=None, placetype='county'):
        """Get all values for a prefix search and point in time

        :param str slug: Slug identifier (or shape id).
        :param str source: Source
        :param str category: Category
        :param str metric: Metric
        :param str date: Date
        :param str placetype: Restrict results to a particular place type.

        """
        params = {}

        if source:
            params['source'] = source

        if category:
            params['category'] = category

        if metric:
            params['metric'] = metric

        if date:
            params['date'] = date

        if placetype:
            params['placetype'] = placetype

        r = self.session.get('%s/data/%s' % (self.url, slug),
                             params=params, timeout=self.TIMEOUT)

        return r.json()

    def statistics(self, slug, source=None, category=None, metric=None):
        """Get a time series for a specific place

        :param str slug: Slug identifier (or shape id).
        :param str slug: Slug identifier (or shape id).
        :param str source: Source
        :param str category: Category
        :param str metric: Metric

        """
        params = {}

        if source:
            params['source'] = source

        if category:
            params['category'] = category

        if metric:
            params['metric'] = metric

        r = self.session.get('%s/statistics/%s' % (self.url, slug),
                             params=params, timeout=self.TIMEOUT)

        return r.json()

    def value(self, slug, source=None, category=None, metric=None, date=None):
        """Get point values for a specific place

        :param str slug: Slug identifier (or shape id).
        :param list(str) source: Source(s)
        :param list(str) category: Category(s)
        :param list(str) metric: Metric(s)
        :param str date: Date
        """
        params = {}

        if source:

            if isinstance(source, string_types):
                source = [source]

            params['source'] = source

        if category:

            if isinstance(category, string_types):
                category = [category]

            params['category'] = category

        if metric:

            if isinstance(metric, string_types):
                metric = [metric]

            params['metric'] = metric

        if date:
            params['date'] = date

        r = self.session.get('%s/value/%s' % (self.url, slug),
                             params=params, timeout=self.TIMEOUT)

        return r.json()
