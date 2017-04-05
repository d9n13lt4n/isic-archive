#!/usr/bin/env python
# -*- coding: utf-8 -*-

###############################################################################
#  Copyright Kitware Inc.
#
#  Licensed under the Apache License, Version 2.0 ( the "License" );
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
###############################################################################

from girder.constants import SettingDefault
from girder.models.model_base import ValidationException
from girder.utility import setting_utilities


class PluginSettings(object):
    DEMO_MODE = 'isic.demo_mode'
    MAX_ISIC_ID = 'isic.max_isic_id'


@setting_utilities.validator(PluginSettings.DEMO_MODE)
def validateDemoModeSetting(doc):
    if not isinstance(doc['value'], bool):
        raise ValidationException('Demo mode must be provided as a boolean.', 'value')


@setting_utilities.validator(PluginSettings.MAX_ISIC_ID)
def validateMaxIsicIdSetting(doc):
    # TODO: can we disable this from being set via the HTTP API?
    if not isinstance(doc['value'], int):
        raise ValidationException('Maximum ISIC ID must be provided as an integer.', 'value')


def registerDefaults():
    SettingDefault.defaults[PluginSettings.DEMO_MODE] = False
    SettingDefault.defaults[PluginSettings.MAX_ISIC_ID] = -1