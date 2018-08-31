# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

from decouple import config
from flask import request
import json

# TAAR specific libraries
from .production import TaarLiteAppResource
from srgutil.context import default_context

# These are configurations that are specific to the TAAR library
TAAR_MAX_RESULTS = config('TAAR_MAX_RESULTS', default=4, cast=int)


class ResourceProxy(object):
    def __init__(self):
        self._resource = None

    def setResource(self, rsrc):
        self._resource = rsrc

    def getResource(self):
        return self._resource


PROXY_MANAGER = ResourceProxy()


def configure_plugin(app):
    """
    This is a factory function that configures all the routes for
    flask given a particular library.
    """
    @app.route('/taarlite/api/v1/addon_recommendations/<string:guid>/')
    def recommendations(guid):
        """Return a list of recommendations provided a telemetry client_id."""
        # Use the module global PROXY_MANAGER
        global PROXY_MANAGER

        if PROXY_MANAGER.getResource() is None:
            ctx = default_context()

            # Lock the context down after we've got basic bits installed
            root_ctx = ctx.child()

            instance = TaarLiteAppResource(root_ctx)
            PROXY_MANAGER.setResource(instance)

        instance = PROXY_MANAGER.getResource()

        client_dict = {'guid': guid}
        normalization_type = request.args.get('normalize', None)
        if normalization_type is not None:
            client_dict['normalize'] = normalization_type

        recommendations = instance.recommend(client_data=client_dict,
                                             limit=TAAR_MAX_RESULTS)

        if len(recommendations) != TAAR_MAX_RESULTS:
            recommendations = []

        # Strip out weights from TAAR results to maintain compatibility
        # with TAAR 1.0
        jdata = {"results": [x[0] for x in recommendations]}

        response = app.response_class(
                response=json.dumps(jdata),
                status=200,
                mimetype='application/json'
                )
        return response

    class MyPlugin:
        def set(self, config_options):
            """
            This setter is primarily so that we can instrument the
            cached RecommendationManager implementation under test.

            All plugins should implement this set method to enable
            overwriting configuration options with a TAAR library.
            """
            global PROXY_MANAGER
            if 'PROXY_RESOURCE' in config_options:
                PROXY_MANAGER._resource = config_options['PROXY_RESOURCE']

    return MyPlugin()
