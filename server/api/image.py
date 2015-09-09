#!/usr/bin/env python
# -*- coding: utf-8 -*-

from girder.api import access
from girder.api.rest import Resource, RestException, loadmodel
from girder.api.describe import Description
from girder.constants import AccessType

from ..image_processing import fillImageGeoJSON


class ImageResource(Resource):
    def __init__(self,):
        self.resourceName = 'image'

        # TODO: change to GET
        self.route('POST', (':id', 'segment-boundary'), self.segmentBoundary)


    @access.user
    @loadmodel(model='item', map={'id': 'image'}, level=AccessType.READ)
    def segmentBoundary(self, image, params):
        body_json = self.getBodyJson()
        self.requireParams(('seed', 'tolerance'), body_json)

        # validate parameters
        seed_point = body_json['seed']
        if not (
            isinstance(seed_point, list) and
            len(seed_point) == 2 and
            all(isinstance(value, int) for value in seed_point)
        ):
            raise RestException('Submitted "seed" must be a coordinate pair.')

        tolerance = body_json['tolerance']
        if not isinstance(tolerance, int):
            raise RestException('Submitted "tolerance" must be an integer.')

        image_data = self.model('image', 'isic_archive').binaryImageRaw(image)

        results = fillImageGeoJSON(
            image_data=image_data,
            seed_point=seed_point,
            tolerance=tolerance
        )

        return results
        # return json.dumps(results)

    segmentBoundary.description = (
        Description('Return the boundary segmentation for an image.')
        # .responseClass('Image')
        .param('id', 'The ID of the image.', paramType='path')
        .param('id', 'The ID of the image.', paramType='path')
        .errorResponse('ID was invalid.'))
