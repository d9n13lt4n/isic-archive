import itertools
import mimetypes
import os
import secrets
from typing import List, Optional, Tuple

import numpy

from girder.constants import AccessType
from girder.exceptions import AccessException
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.item import Item
from girder.models.upload import Upload

from .dataset import Dataset
from .dataset_helpers.image_metadata import addImageMetadata
from .segmentation_helpers import ScikitSegmentationHelper
from .user import User


class Image(Item):

    imageDefaults = {
        'ingested': False,
        'readable': None,
        'ingestionState': {
            'largeImage': None,
            'superpixelMask': None
        },
        'largeImage': {
            'sourceName': None,
            'originalId': None,
            'fileId': None
        },
        'superpixelsId': None,
    }

    def initialize(self):
        super(Image, self).initialize()

        # Ensure CSV metadata matching is fast
        self.ensureIndices(['privateMeta.originalFilename'])

        self.prefixSearchFields = ['lowerName', 'name']

    @staticmethod
    def generateIsicId():
        taken = True
        id_: int = 0

        while taken:
            id_ = secrets.randbelow(10**7)
            isicId = f'ISIC_{id_:07d}'
            taken = Image().find({'name': isicId}).count() > 0

        return isicId

    def renameImage(self, image, newName):
        # assumes newName is of the format "ISIC_0123456"
        oldName = image['name']
        image['name'] = newName
        for childFile in self.childFiles(image):
            childFile['name'] = childFile['name'].replace(oldName, newName)
            File().save(childFile)

        return Image().save(image)

    def createEmptyImage(self, originalFileRelpath, parentFolder, creator, dataset,
                         batch):
        newIsicId = self.generateIsicId()
        image = self.createItem(
            name=newIsicId,
            creator=creator,
            folder=parentFolder,
            description=''
        )

        image['privateMeta'] = {
            'originalFilename': os.path.basename(originalFileRelpath),
            'originalFileRelpath': originalFileRelpath
        }
        image['meta'] = {
            'acquisition': {},
            'clinical': {},
            'unstructured': {},
            'unstructuredExif': {},
            'tags': [],
            'datasetId': dataset['_id'],
            'batchId': batch['_id']
        }
        image.update(self.imageDefaults)
        image = Image().save(image)

        return image

    def resetImageForIngest(self, image):
        for childFile in self.childFiles(image):
            if childFile['imageRole'] != 'original':
                File().remove(childFile)

        image.update(self.imageDefaults)

        return Image().save(image)

    def resetMetadata(self, image):
        if 'pixelsX' in image['meta']['acquisition']:
            image['meta']['acquisition'] = {
                'pixelsX': image['meta']['acquisition']['pixelsX'],
                'pixelsY': image['meta']['acquisition']['pixelsY']
            }
        else:
            image['meta']['acquisition'] = {}
        image['meta']['clinical'] = {}
        image['meta']['unstructured'] = {}
        image['meta']['unstructuredExif'] = {}

        if 'age' in image['privateMeta']:
            del image['privateMeta']['age']

        image = Image().save(image)
        return image

    def createImage(self, imageDataStream, imageDataSize, originalFileRelpath,
                    parentFolder, creator, dataset, batch):
        image = self.createEmptyImage(originalFileRelpath, parentFolder, creator, dataset, batch)

        # Upload().uploadFromFile will do nothing if the image is empty
        # See: https://github.com/girder/girder/issues/2773
        if imageDataSize:
            Upload().uploadFromFile(
                obj=imageDataStream,
                size=imageDataSize,
                name='%s%s' % (
                    image['name'],
                    os.path.splitext(os.path.basename(originalFileRelpath))[1].lower()
                ),
                parentType='item',
                parent=image,
                user=creator,
                mimeType=mimetypes.guess_type(os.path.basename(originalFileRelpath))[0],
            )

        # TODO: copy license from dataset to image
        return image

    def originalFile(self, image) -> Optional[dict]:
        return File().findOne({
            'itemId': image['_id'],
            'imageRole': 'original'
        })

    def strippedFile(self, image):
        return File().findOne({'itemId': image['_id'],
                               'stripped': True}, limit=1)

    def superpixelsFile(self, image):
        return File().load(
            image['superpixelsId'], force=True, exc=True)

    def _decodeDataFromFile(self, fileObj):
        filePath = File().getLocalFilePath(fileObj)
        # Scikit-Image is ~70ms faster at decoding image data
        data = ScikitSegmentationHelper.loadImage(filePath)
        return data

    def imageData(self, image) -> numpy.ndarray:
        """Return the RGB image data associated with this image."""
        imageFile = self.originalFile(image)
        imageData = self._decodeDataFromFile(imageFile)
        return imageData

    def superpixelsData(self, image) -> numpy.ndarray:
        """Return the superpixel label data associated with this image."""
        superpixelsFile = self.superpixelsFile(image)
        superpixelsRGBData = self._decodeDataFromFile(superpixelsFile)
        superpixelsLabelData = ScikitSegmentationHelper._RGBTounit64(
            superpixelsRGBData)
        return superpixelsLabelData

    def _findQueryFilter(self, query):
        # assumes collection has been created by provision_utility
        # TODO: cache this value
        imageCollection = Collection().findOne(
            {'name': 'Lesion Images'},
            fields={'_id': 1}
        )

        # TODO: this will also include Pre-review images; should it?
        newQuery = query.copy() if query is not None else {}
        newQuery.update({
            'baseParentId': imageCollection['_id']
        })
        return newQuery

    def find(self, query=None, **kwargs):
        imageQuery = self._findQueryFilter(query)
        return super(Image, self).find(imageQuery, **kwargs)

    def findOne(self, query=None, **kwargs):
        imageQuery = self._findQueryFilter(query)
        return super(Image, self).findOne(imageQuery, **kwargs)

    def filter(self, image, user=None, additionalKeys=None):
        output = {
            '_id': image['_id'],
            '_modelType': 'image',
            'name': image['name'],
            'created': image['created'],
            'creator': User().filterSummary(
                User().load(image['creatorId'], force=True, exc=True),
                user),
            # TODO: verify that "updated" is set correctly
            'updated': image['updated'],
            'dataset': Dataset().filterSummary(
                Dataset().load(image['meta']['datasetId'], force=True, exc=True),
                user),
            'meta': {
                'acquisition': image['meta']['acquisition'],
                'clinical': image['meta']['clinical'],
            },
            'notes': {
                'reviewed': image['meta'].get('reviewed', None),
                'tags': image['meta']['tags']
            }
        }
        if User().canReviewDataset(user):
            output['meta']['unstructured'] = image['meta']['unstructured'],
            output['meta']['unstructuredExif'] = image['meta']['unstructuredExif']
            output['meta']['private'] = image['privateMeta']

        return output

    def filterSummary(self, image, user=None):
        return {
            '_id': image['_id'],
            'name': image['name'],
            'updated': image['updated'],
        }

    def load(self, id, level=AccessType.ADMIN, user=None, objectId=True, force=False, fields=None,
             exc=False):
        # Avoid circular import
        from .study import Study

        # Allow annotators assigned to an image to always have read access to that image.

        # TODO: Ideally, this might set Image().resourceColl to Dataset, then add the special case
        # checks in Dataset().hasAccess. However, since AccessControlMixin.resourceColl doesn't work
        # properly (yet) with plugin types, and since we really only care about the cases where an
        # image is loaded directly (rather than when all images or datasets are iterated over);
        # adding the special case logic here works fine for now.

        try:
            return super(Image, self).load(
                id, level=level, user=user, objectId=objectId, force=force, fields=fields, exc=exc)
        except AccessException:
            image = self.load(id, objectId=objectId, force=True, fields=fields, exc=exc)
            if Study().childAnnotations(annotatorUser=user, image=image).count():
                return image
            else:
                raise

    def getHistograms(self, filterQuery, user):
        # Define facets
        categorialFacets = [
            'meta.datasetId',
            'meta.clinical.benign_malignant',
            'meta.clinical.sex',
            'meta.clinical.diagnosis_confirm_type',
            'meta.clinical.diagnosis',
            'meta.clinical.nevus_type',
            'meta.clinical.melanocytic',
            'meta.clinical.personal_hx_mm',
            'meta.clinical.family_hx_mm',
            'meta.clinical.mel_class',
            'meta.clinical.mel_type',
            'meta.clinical.mel_mitotic_index',
            'meta.clinical.mel_ulcer',
            'meta.clinical.anatom_site_general',
            'meta.acquisition.image_type',
            'meta.acquisition.dermoscopic_type',
            'meta.acquisition.blurry',
            'meta.acquisition.color_tint',
            'meta.acquisition.hairy',
            'meta.acquisition.marker_pen'
        ]
        tagFacets = [
            'meta.tags'
        ]
        ordinalFacets = [
            (
                'meta.clinical.age_approx',
                [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]
            ),
            (
                'meta.clinical.clin_size_long_diam_mm',
                # [0.0, 2.0, 4.0, 6.0, 8.0, 10.0, 12.0, 14.0,
                #  16.0, 18.0, 20.0, 100.0, 200.0, 1000.0])
                [0.0, 10.0, 20.0, 30.0, 40.0, 50.0, 60.0,
                 70.0, 80.0, 90.0, 100.0, 110.0]
            ),
            (
                'meta.clinical.mel_thick_mm',
                [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0]
            )
        ]

        # Build and run the pipeline
        folderQuery = {
            'folderId': {'$in': [
                dataset['folderId'] for dataset in Dataset().list(user=user)]}
        }
        if filterQuery:
            query = {
                '$and': [
                    folderQuery,
                    filterQuery
                ]
            }
        else:
            query = folderQuery
        facetStages = {
            '__passedFilters__': [
                {'$count': 'count'}],
        }
        for facetName in categorialFacets:
            facetId = facetName.replace('.', '__')
            facetStages[facetId] = [
                {'$sortByCount': f'${facetName}'}
            ]
        for facetName in tagFacets:
            facetId = facetName.replace('.', '__')
            facetStages[facetId] = [
                {'$unwind': {
                    'path': f'${facetName}',
                    'preserveNullAndEmptyArrays': True
                }},
                {'$sortByCount': f'${facetName}'}
            ]
        for facetName, boundaries in ordinalFacets:
            facetId = facetName.replace('.', '__')
            facetStages[facetId] = [
                {'$bucket': {
                    'groupBy': f'${facetName}',
                    'boundaries': boundaries,
                    'default': None
                }}
            ]
        histogram = next(iter(self.collection.aggregate([
            {'$match': query},
            {'$facet': facetStages}
        ])))

        # Fix up the pipeline result
        if not histogram['__passedFilters__']:
            # If the set of filtered images is empty, add a count manually
            histogram['__passedFilters__'] = [{'count': 0}]
        histogram['__passedFilters__'][0]['label'] = 'count'
        for facetName in itertools.chain(
                categorialFacets,
                tagFacets,
                [facetName for facetName, boundaries in ordinalFacets]
        ):
            facetId = facetName.replace('.', '__')
            histogram[facetName] = histogram.pop(facetId, [])
            histogram[facetName].sort(
                # Sort facet bins, placing "None" at the end
                key=lambda facetBin: (facetBin['_id'] is None, facetBin['_id']))
        for facetName in itertools.chain(categorialFacets, tagFacets):
            for facetBin in histogram[facetName]:
                facetBin['label'] = facetBin.pop('_id')
        for facetName, boundaries in ordinalFacets:
            boundariesMap = {
                lowBound: {
                    'label': f'[{lowBound} - {highBound})',
                    'lowBound': lowBound,
                    'highBound': highBound,
                }
                for lowBound, highBound in zip(boundaries, boundaries[1:])
            }
            for facetBin in histogram[facetName]:
                # Remove the '_id' field and replace it with the 3 other fields
                binId = facetBin.pop('_id')
                if binId is not None:
                    facetBin.update(boundariesMap[binId])
                else:
                    facetBin['label'] = None

        return histogram

    def remove(self, image, **kwargs):
        # Avoid circular import
        from .segmentation import Segmentation
        from .annotation import Annotation

        for annotation in Annotation().find({'imageId': image['_id']}):
            Annotation().remove(annotation)

        for segmentation in Segmentation().find({'imageId': image['_id']}):
            Segmentation().remove(segmentation)

        return super(Image, self).remove(image)

    def validate(self, doc):
        # TODO: implement
        return super(Image, self).validate(doc)

    def applyMetadata(self, image, metadata, save) -> Tuple[List[str], List[str]]:
        """
        Apply metadata to an image.

        :param image: Image document.
        :param metadata: Image metadata.
        :param save: Whether to save the metadata to the image if validation succeeds.
        :return: Tuple of:
            - List of strings describing validation errors.
            - List of strings describing metadata warnings.
        """
        errors, warnings = addImageMetadata(image, metadata)

        if not errors and save:
            self.save(image)

        return errors, warnings
