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

import six


class MetadataFieldException(Exception):
    """Base class for exceptions raised while parsing metadata fields."""
    pass


class MetadataFieldNotFoundException(MetadataFieldException):
    """Exception raised when none of the fields that a parser supports are found."""
    def __init__(self, fields):
        super(MetadataFieldNotFoundException, self).__init__()
        self.fields = fields


class MetadataValueExistsException(MetadataFieldException):
    """Exception raised when a value for a field already exists and can't be safely overwritten."""
    def __init__(self, name, oldValue, newValue):
        super(MetadataValueExistsException, self).__init__()
        self.name = name
        self.oldValue = oldValue
        self.newValue = newValue


class MultipleFieldException(MetadataFieldException):
    """Exception raised when more than one fields that a parser supports are found."""
    def __init__(self, name, fields):
        super(MultipleFieldException, self).__init__()
        self.name = name
        self.fields = fields


class BadFieldTypeException(MetadataFieldException):
    """Exception raised when the value for a field is the wrong type."""
    def __init__(self, name, fieldType, value):
        super(BadFieldTypeException, self).__init__()
        self.name = name
        self.fieldType = fieldType
        self.value = value


class FieldParser(object):
    name = ''
    allowedFields = {}

    @classmethod
    def run(cls, data, clinical, private):
        try:
            rawValue = cls.extract(data)
        except MetadataFieldNotFoundException:
            # The field doesn't exist in the given data, which is harmless
            return

        cleanValue = cls.transform(rawValue)
        cls.load(cleanValue, clinical, private)

    @classmethod
    def extract(cls, data):
        """
        Extract the value for this parser's field.
        Field keys in data are matched case insensitively.
        A MetadataFieldNotFoundException is raised if none of the allowed fields are found.
        A MultipleFieldException is raised if more than one of the allowed fields are found.
        """
        availableFields = six.viewkeys(data)
        allowedFields = set(field.lower() for field in cls.allowedFields)

        foundFields = [field for field
                       in availableFields
                       if field.lower() in allowedFields]

        if not foundFields:
            raise MetadataFieldNotFoundException(fields=cls.allowedFields)
        if len(foundFields) > 1:
            raise MultipleFieldException(name=cls.name, fields=sorted(foundFields))

        field = foundFields.pop()
        value = data.pop(field)

        assert(value is None or isinstance(value, six.string_types))

        return value

    @classmethod
    def transform(cls, value):
        """
        Implement in subclasses. Values that are None, match the empty string,
        or 'unknown' (ignoring case) should be coerced to None.
        """
        raise NotImplementedError()

    @classmethod
    def load(cls, value, clinical, private):
        """Implement in subclasses."""
        raise NotImplementedError()

    @classmethod
    def _coerceInt(cls, value):
        try:
            value = int(float(value))
        except ValueError:
            raise BadFieldTypeException(name=cls.name, fieldType='integer', value=value)
        return value

    @classmethod
    def _coerceFloat(cls, value):
        try:
            value = float(value)
        except ValueError:
            raise BadFieldTypeException(name=cls.name, fieldType='float', value=value)
        return value

    @classmethod
    def _coerceBool(cls, value):
        if value in ['true', 'yes']:
            return True
        elif value in ['false', 'no']:
            return False
        else:
            raise BadFieldTypeException(name=cls.name, fieldType='boolean', value=value)

    @classmethod
    def _assertEnumerated(cls, value, allowed):
        if value not in allowed:
            expected = 'one of %s' % str(sorted(allowed))
            raise BadFieldTypeException(name=cls.name, fieldType=expected, value=value)

    @classmethod
    def _checkWrite(cls, metadata, key, value):
        """
        Check that the value for the key can safely be written. The following scenarios allow
        writes:
        - the old value doesn't exist in the metadata dictionary
        - the old value is None
        - the old value matches the new value

        Otherwise, a MetadataValueExistsException is raised.
        """
        oldValue = metadata.get(key)
        if (oldValue is not None) and (oldValue != value):
            raise MetadataValueExistsException(name=key, oldValue=oldValue, newValue=value)


class AgeFieldParser(FieldParser):
    name = 'age'
    approxName = 'age_approx'
    allowedFields = {'age'}

    @classmethod
    def transform(cls, value):
        if value is not None:
            value = value.strip()
            value = value.lower()
            if value in ['', 'unknown']:
                value = None
            else:
                if value == '85+':
                    value = '85'
                value = cls._coerceInt(value)
                if value > 85:
                    value = 85
        return value

    @classmethod
    def load(cls, value, clinical, private):
        approxAge = \
            int(round(value / 5.0) * 5) \
            if value is not None \
            else None

        cls._checkWrite(private, cls.name, value)
        cls._checkWrite(clinical, cls.approxName, approxAge)

        private[cls.name] = value
        clinical[cls.approxName] = approxAge


class SexFieldParser(FieldParser):
    name = 'sex'
    allowedFields = {'sex', 'gender'}

    @classmethod
    def transform(cls, value):
        if value is not None:
            value = value.strip()
            value = value.lower()
            if value in ['', 'unknown']:
                value = None
            else:
                if value == 'm':
                    value = 'male'
                elif value == 'f':
                    value = 'female'
                cls._assertEnumerated(value, {'male', 'female'})
        return value

    @classmethod
    def load(cls, value, clinical, private):
        cls._checkWrite(clinical, cls.name, value)
        clinical[cls.name] = value


class HxMmFieldParser(FieldParser):
    @classmethod
    def transform(cls, value):
        if value is not None:
            value = value.strip()
            value = value.lower()
            if value in ['', 'unknown']:
                value = None
            else:
                value = cls._coerceBool(value)
        return value

    @classmethod
    def load(cls, value, clinical, private):
        cls._checkWrite(clinical, cls.name, value)
        clinical[cls.name] = value


class FamilyHxMmFieldParser(HxMmFieldParser):
    name = 'family_hx_mm'
    allowedFields = {'family_hx_mm', 'FamHxMM'}


class PersonalHxMmFieldParser(HxMmFieldParser):
    name = 'personal_hx_mm'
    allowedFields = {'personal_hx_mm'}


class ClinicalSizeFieldParser(FieldParser):
    name = 'clin_size_long_diam_mm'
    allowedFields = {'clin_size_long_diam_mm'}

    @classmethod
    def transform(cls, value):
        if value is not None:
            value = value.strip()
            value = value.lower()
            if value in ['', 'unknown']:
                value = None
            else:
                value = cls._coerceFloat(value)
        return value

    @classmethod
    def load(cls, value, clinical, private):
        cls._checkWrite(clinical, cls.name, value)
        clinical[cls.name] = value


class MelanocyticFieldParser(FieldParser):
    name = 'melanocytic'
    allowedFields = {'melanocytic'}

    @classmethod
    def transform(cls, value):
        if value is not None:
            value = value.strip()
            value = value.lower()
            if value in ['', 'unknown']:
                value = None
            else:
                value = cls._coerceBool(value)
        return value

    @classmethod
    def load(cls, value, clinical, private):
        cls._checkWrite(clinical, cls.name, value)
        clinical[cls.name] = value


class DiagnosisConfirmTypeFieldParser(FieldParser):
    name = 'diagnosis_confirm_type'
    allowedFields = {'diagnosis_confirm_type'}

    @classmethod
    def transform(cls, value):
        if value is not None:
            value = value.strip()
            value = value.lower()
            if value in ['', 'unknown']:
                value = None
            else:
                cls._assertEnumerated(value, {
                    'histopathology',
                    'serial imaging showing no change',
                    'single image expert consensus'})
        return value

    @classmethod
    def load(cls, value, clinical, private):
        cls._checkWrite(clinical, cls.name, value)
        clinical[cls.name] = value


class BenignMalignantFieldParser(FieldParser):
    name = 'benign_malignant'
    allowedFields = {'benign_malignant', 'ben_mal'}

    @classmethod
    def transform(cls, value):
        if value is not None:
            value = value.strip()
            value = value.lower()
            if value in ['', 'unknown']:
                value = None
            else:
                if value == 'indeterminable':
                    value = 'indeterminate'
                cls._assertEnumerated(value, {
                    'benign',
                    'malignant',
                    'indeterminate',
                    'indeterminate/benign',
                    'indeterminate/malignant'})
        return value

    @classmethod
    def load(cls, value, clinical, private):
        cls._checkWrite(clinical, cls.name, value)
        clinical[cls.name] = value

#
# if 'diagnosis_confirm_type' not in clinical:
#             # TODO: remove this, it's always going to be there
#             raise Exception('"diagnosis_confirm_type" must also be set')
#
#         if value in {'malignant', 'indeterminate/malignant'}:
#             if clinical['diagnosis_confirm_type'] != 'histopathology':
#                 raise Exception(
#                     'if this value is "malignant", "diagnosis_confirm_type" '
#                     'must be "histopathology"')


class DiagnosisFieldParser(FieldParser):
    name = 'diagnosis'
    allowedFields = {'diagnosis', 'path_diagnosis'}

    @classmethod
    def transform(cls, value):
        if value is not None:
            value = value.strip()
            value = value.lower()
            if value in ['', 'unknown']:
                value = None
            else:
                if value == 'aimp':
                    value = 'AIMP'
                elif value == 'lentigo nos':
                    value = 'lentigo NOS'
                elif value == u'caf\xe9-au-lait macule':
                    # Deal with a possible unicode char in "cafe-au-lait macule"
                    # TODO: instead, actually use the unicode char here
                    value = 'cafe-au-lait macule'
                cls._assertEnumerated(value, {
                    'actinic keratosis',
                    'adnexal tumor',
                    'AIMP',
                    'angiokeratoma',
                    'angioma',
                    'basal cell carcinoma',
                    'cafe-au-lait macule',
                    'dermatofibroma',
                    'ephelis',
                    'lentigo NOS',
                    'lentigo simplex',
                    'lichenoid keratosis',
                    'melanoma',
                    'melanoma metastasis',
                    'merkel cell carcinoma',
                    'mucosal melanosis',
                    'nevus',
                    'nevus spilus',
                    'seborrheic keratosis',
                    'solar lentigo',
                    'squamous cell carcinoma',
                    'clear cell acanthoma',
                    'atypical spitz tumor',
                    'acrochordon',
                    'angiofibroma or fibrous papule',
                    'neurofibroma',
                    'pyogenic granuloma',
                    'scar',
                    'sebaceous adenoma',
                    'sebaceous hyperplasia',
                    'verruca',
                    'atypical melanocytic proliferation',
                    'epidermal nevus',
                    'other'})
        return value

    @classmethod
    def load(cls, value, clinical, private):
        cls._checkWrite(clinical, cls.name, value)
        clinical[cls.name] = value


class NevusTypeFieldParser(FieldParser):
    name = 'nevus_type'
    allowedFields = {'nevus_type'}

    @classmethod
    def transform(cls, value):
        if value is not None:
            value = value.strip()
            value = value.lower()
            if value in ['', 'unknown']:
                value = None
            elif value == 'not applicable':
                value = None
            else:
                # TODO: finish this
                cls._assertEnumerated(value, {
                    'blue',
                    'combined',
                    'nevus NOS',
                    'deep penetrating',
                    'halo',
                    'other',
                    'persistent/recurrent',
                    'pigmented spindle cell of reed',
                    'plexiform spindle cell',
                    'special site',
                    'spitz',
                    #             'not applicable'
                    'unknown'})
        return value

    @classmethod
    def load(cls, value, clinical, private):
        cls._checkWrite(clinical, cls.name, value)
        clinical[cls.name] = value

#     if 'diagnosis' in clinical:


# allowed_diagnoses = {'nevus', 'nevus spilus', 'epidermal nevus'}
#         if clinical['path_diagnosis'] not in allowed_diagnoses:
#             raise Exception(
#                 'if this value is set, "path_diagnosis" must be one of %s' %
#                 sorted(allowed_diagnoses))


def addImageClinicalMetadata(image, data):
    """
    Add clinical metadata to an image. Data is expected to be a row from
    csv.DictReader. Values for recognized fields are parsed and added to the
    image's clinical metadata field and private metadata field. Unrecognized
    fields are added to the image's unstructured metadata field.

    Returns a list of descriptive errors with the metadata. An empty list
    indicates that there are no errors.

    :param image: The image.
    :type image: dict
    :param data: The image metadata.
    :type data: dict
    :return: List of errors with the metadata.
    :rtype: list of strings
    """
    errors = []

    for parser in [
        AgeFieldParser,
        SexFieldParser,
        FamilyHxMmFieldParser,
        PersonalHxMmFieldParser,
        ClinicalSizeFieldParser,
        MelanocyticFieldParser,
        DiagnosisConfirmTypeFieldParser,
        BenignMalignantFieldParser,
        DiagnosisFieldParser,
        # NevusTypeFieldParser,
    ]:
        clinical = image['meta']['clinical']
        private = image['privateMeta']

        try:
            parser.run(data, clinical, private)
        except MetadataValueExistsException as e:
            errors.append(
                'value already exists for field %r (old: %r, new: %r)' %
                (e.name, e.oldValue, e.newValue))
        except MultipleFieldException as e:
            errors.append(
                'only one of field %r may be present, found: %r' %
                (e.name, e.fields))
        except BadFieldTypeException as e:
            errors.append(
                'value is wrong type for field %r (expected %r, value: %r)' %
                (e.name, e.fieldType, e.value))

    # TODO: handle contingently required fields and inter-field validation

    # Add remaining data as unstructured metadata
    image['meta']['unstructured'].update(data)

    return errors
