# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.apps import AppConfig

from openedx.core.djangoapps.plugins.constants import ProjectType, PluginURLs


class MobileScormSyncConfig(AppConfig):
    name = 'scorm_app'

    plugin_app = {
        PluginURLs.CONFIG: {
            ProjectType.LMS: {
                PluginURLs.NAMESPACE: 'scorm_app',
                PluginURLs.APP_NAME: 'scorm_app',
                PluginURLs.REGEX: '^mobile_xblock_sync/',
                PluginURLs.RELATIVE_PATH: 'urls',
            }
        }
    }
