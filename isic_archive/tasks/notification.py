import pymongo

from girder.models.user import User
from girder.utility import mail_utils

from isic_archive.models import Batch, Dataset, Image
from isic_archive.tasks import app
from isic_archive.utility.mail_utils import sendEmail, sendEmailToGroup


@app.task()
def maybeSendIngestionNotifications():
    for batch in Batch().find({'ingestStatus': 'extracted'}):
        if not Batch().hasImagesPendingIngest(batch):
            # TODO: Move sorting to templating since it's a rendering concern?
            failedImages = list(Image().find({
                'meta.batchId': batch['_id'],
                '$or': [
                    {'ingestionState.largeImage': False},
                    {'ingestionState.superpixelMask': False}
                ]
            }, fields=['privateMeta.originalFilename']).sort(
                'privateMeta.originalFilename',
                pymongo.ASCENDING
            ))
            skippedFilenames = list(Image().find({
                'meta.batchId': batch['_id'],
                'readable': False
            }, fields=['privateMeta.originalFilename']).sort(
                'privateMeta.originalFilename',
                pymongo.ASCENDING
            ))

            sendIngestionNotification.delay(batch['_id'], failedImages, skippedFilenames)
            batch['ingestStatus'] = 'notified'
            Batch().save(batch)


@app.task()
def sendIngestionNotification(batchId, failedImages, skippedFilenames):
    batch = Batch().load(batchId)
    dataset = Dataset().load(batch['datasetId'], force=True)
    user = User().load(batch['creatorId'], force=True)
    host = mail_utils.getEmailUrlPrefix()
    # TODO: The email should gracefully handle the situation where failedImages or skippedFilenames
    # has an excessive amount of items.
    params = {
        'isOriginalUploader': True,
        'host': host,
        'dataset': dataset,
        # We intentionally leak full user details here, even though all
        # email recipients may not have access permissions to the user
        'user': user,
        'batch': batch,
        'failedImages': failedImages,
        'skippedFilenames': skippedFilenames
    }
    subject = 'ISIC Archive: Dataset Upload Confirmation'
    templateFilename = 'ingestDatasetConfirmation.mako'

    # Mail user
    html = mail_utils.renderTemplate(templateFilename, params)
    sendEmail(to=user['email'], subject=subject, text=html)

    # Mail 'Dataset QC Reviewers' group
    params['isOriginalUploader'] = False
    sendEmailToGroup(
        groupName='Dataset QC Reviewers',
        templateFilename=templateFilename,
        templateParams=params,
        subject=subject)