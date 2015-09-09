#!/usr/bin/env python
# -*- coding: utf-8 -*-

import collections
import datetime
import json

from bson import ObjectId
import pymongo

from girder.api import access
from girder.api.rest import Resource, RestException, loadmodel
from girder.api.describe import Description
from girder.constants import AccessType

from ..provision_utility import ISIC


class AnnotationResource(Resource):
    def __init__(self, plugin_root_dir):
        self.resourceName = 'annotation'
        self.plugin_root_dir = plugin_root_dir

        self.route('GET', (':annotation_id',), self.getAnnotation)
        self.route('PUT', (':annotation_id',), self.submitAnnotation)


    # TODO: move this to an image model
    def _getSegmentationInfo(self, image):
        # get the most recent file from p1b or p1c
        item_file = self.model('file').findOne(
            query={
                'itemId': image['_id'],
                'name': {'$regex': 'p1[bc]\.json$'}
            },
            sort=[('created', pymongo.DESCENDING)]
        )
        if item_file:
            item_file_generator = self.model('file').download(item_file, headers=False)
            segmentation_info = json.loads(''.join(item_file_generator()))

            # this first dict level will always contain a single item called
            #   'p1b' or 'p1c', but we're not sure which
            return segmentation_info.values()[0]
        else:
            return None


    @access.user
    @loadmodel(model='annotation', plugin='isic_archive', map={'annotation_id': 'annotation_item'}, level=AccessType.READ)
    def getAnnotation(self, annotation_item, params):
        # return self.model('annotation', 'isic_archive').filter(annotation_item, , self.getCurrentUser())
        image = self.model('item').load(annotation_item['meta']['imageId'], force=True)
        study = self.model('study', 'isic_archive').load(annotation_item['meta']['studyId'], force=True)
        featureset = self.model('featureset', 'isic_archive').load(study['meta']['featuresetId'])

        return_dict = {
            'image': image
        }

        segmentation_info = self._getSegmentationInfo(image)
        if not segmentation_info:
            # TODO: no file found
            raise Exception()
        return_dict['segmentation_info'] = segmentation_info['steps']

        # transform featureset to legacy format
        legacy_featureset = dict()
        for new_level, legacy_level in [
                ('image_features', 'lesionlevel'),
                ('region_features', 'tiles')
                ]:
            # need to first build an intermediate variable to maintain ordering
            legacy_questions = collections.OrderedDict()

            for feature in featureset[new_level]:
                header = feature['name'][0]
                legacy_question = {
                    'name': feature['name'][0] if len(feature['name']) == 1 else ': '.join(feature['name'][1:]),
                    'type': feature['type']
                }
                if feature['type'] == 'select':
                    legacy_question['shortname'] = feature['id']
                    legacy_question['options'] = feature['options']
                else:
                    legacy_question['id'] = feature['id']
                legacy_questions.setdefault(header, list()).append(legacy_question)

            legacy_featureset[legacy_level] = [
                {'header': header, 'questions': questions}
                for header, questions in legacy_questions.iteritems()
            ]
        return_dict['features'] = legacy_featureset

        return return_dict

    getAnnotation.description = (
        Description('Get annotation details.')
        .param('annotation_id', 'The ID of the annotation to be fetched.', paramType='path')
        .errorResponse())


    @access.user
    @loadmodel(model='annotation', plugin='isic_archive', map={'annotation_id': 'annotation_item'}, level=AccessType.READ)
    def submitAnnotation(self, annotation_item, params):
        if annotation_item['baseParentId'] != ISIC.AnnotationStudies.collection['_id']:
            raise RestException('Annotation id references a non-annotation item.')

        if annotation_item['meta']['userId'] != self.getCurrentUser()['_id']:
            raise RestException('Current user does not own this annotation.')

        if annotation_item['meta'].get('stopTime'):
            raise RestException('Annotation is already complete.')

        body_json = self.getBodyJson()
        self.requireParams(('imageId', 'startTime', 'stopTime', 'annotations'), body_json)

        if ObjectId(body_json['imageId']) != annotation_item['meta']['imageId']:
            raise RestException('Submitted imageId is incorrect.')

        annotation_item['meta']['startTime'] = \
            datetime.datetime.utcfromtimestamp(body_json['startTime'] / 1000.0)
        annotation_item['meta']['stopTime'] = \
            datetime.datetime.utcfromtimestamp(body_json['stopTime'] / 1000.0)
        annotation_item['meta']['annotations'] = body_json['annotations']

        self.model('annotation', 'isic_archive').save(annotation_item)

    submitAnnotation.description = (
        Description('Submit a completed annotation.')
        .param('annotation_id', 'The ID of the annotation to be submitted.', paramType='path')
        .param('body', 'JSON containing the annotation parameters.', paramType='body', required=True)
        .errorResponse())
