# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock
import six
import webob

from cinder.api.contrib import types_manage
from cinder import context
from cinder import exception
from cinder import test
from cinder.tests.unit.api import fakes
from cinder.volume import volume_types


def stub_volume_type(id):
    specs = {"key1": "value1",
             "key2": "value2",
             "key3": "value3",
             "key4": "value4",
             "key5": "value5"}
    return dict(id=id,
                name='vol_type_%s' % six.text_type(id),
                description='vol_type_desc_%s' % six.text_type(id),
                extra_specs=specs)


def stub_volume_type_updated(id, is_public=True):
    return dict(id=id,
                name='vol_type_%s_%s' % (six.text_type(id), six.text_type(id)),
                is_public=is_public,
                description='vol_type_desc_%s_%s' % (
                    six.text_type(id), six.text_type(id)))


def stub_volume_type_updated_desc_only(id):
    return dict(id=id,
                name='vol_type_%s' % six.text_type(id),
                description='vol_type_desc_%s_%s' % (
                    six.text_type(id), six.text_type(id)))


def return_volume_types_get_volume_type(context, id):
    if id == "777":
        raise exception.VolumeTypeNotFound(volume_type_id=id)
    return stub_volume_type(int(id))


def return_volume_types_destroy(context, name):
    if name == "777":
        raise exception.VolumeTypeNotFoundByName(volume_type_name=name)
    pass


def return_volume_types_with_volumes_destroy(context, id):
    if id == "1":
        raise exception.VolumeTypeInUse(volume_type_id=id)
    pass


def return_volume_types_create(context,
                               name,
                               specs,
                               is_public,
                               description):
    pass


def return_volume_types_create_duplicate_type(context,
                                              name,
                                              specs,
                                              is_public,
                                              description):
    raise exception.VolumeTypeExists(id=name)


def stub_volume_type_updated_name_only(id):
    return dict(id=id,
                name='vol_type_%s_%s' % (six.text_type(id), six.text_type(id)),
                description='vol_type_desc_%s' % six.text_type(id))


def stub_volume_type_updated_name_after_delete(id):
    return dict(id=id,
                name='vol_type_%s' % six.text_type(id),
                description='vol_type_desc_%s' % six.text_type(id))


def return_volume_types_get_volume_type_updated(id, is_public=True):
    if id == "777":
        raise exception.VolumeTypeNotFound(volume_type_id=id)
    if id == '888':
        return stub_volume_type_updated_desc_only(int(id))
    if id == '999':
        return stub_volume_type_updated_name_only(int(id))
    if id == '666':
        return stub_volume_type_updated_name_after_delete(int(id))

    # anything else
    return stub_volume_type_updated(int(id), is_public=is_public)


def return_volume_types_get_by_name(context, name):
    if name == "777":
        raise exception.VolumeTypeNotFoundByName(volume_type_name=name)
    return stub_volume_type(int(name.split("_")[2]))


def return_volume_types_get_default():
    return stub_volume_type(1)


def return_volume_types_get_default_not_found():
    return {}


class VolumeTypesManageApiTest(test.TestCase):
    def setUp(self):
        super(VolumeTypesManageApiTest, self).setUp()
        self.flags(host='fake')
        self.controller = types_manage.VolumeTypesManageController()
        """to reset notifier drivers left over from other api/contrib tests"""

    def tearDown(self):
        super(VolumeTypesManageApiTest, self).tearDown()

    def test_volume_types_delete(self):
        self.stubs.Set(volume_types, 'get_volume_type',
                       return_volume_types_get_volume_type)
        self.stubs.Set(volume_types, 'destroy',
                       return_volume_types_destroy)

        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        self.assertEqual(0, len(self.notifier.notifications))
        self.controller._delete(req, 1)
        self.assertEqual(1, len(self.notifier.notifications))

    def test_volume_types_delete_not_found(self):
        self.stubs.Set(volume_types, 'get_volume_type',
                       return_volume_types_get_volume_type)
        self.stubs.Set(volume_types, 'destroy',
                       return_volume_types_destroy)

        self.assertEqual(0, len(self.notifier.notifications))
        req = fakes.HTTPRequest.blank('/v2/fake/types/777')
        self.assertRaises(webob.exc.HTTPNotFound, self.controller._delete,
                          req, '777')
        self.assertEqual(1, len(self.notifier.notifications))

    def test_volume_types_with_volumes_destroy(self):
        self.stubs.Set(volume_types, 'get_volume_type',
                       return_volume_types_get_volume_type)
        self.stubs.Set(volume_types, 'destroy',
                       return_volume_types_with_volumes_destroy)
        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        self.assertEqual(0, len(self.notifier.notifications))
        self.controller._delete(req, 1)
        self.assertEqual(1, len(self.notifier.notifications))

    @mock.patch('cinder.volume.volume_types.destroy')
    @mock.patch('cinder.volume.volume_types.get_volume_type')
    @mock.patch('cinder.policy.enforce')
    def test_volume_types_delete_with_non_admin(self, mock_policy_enforce,
                                                mock_get, mock_destroy):

        # allow policy authorized user to delete type
        mock_policy_enforce.return_value = None
        mock_get.return_value = \
            {'extra_specs': {"key1": "value1"},
             'id': 1,
             'name': u'vol_type_1',
             'description': u'vol_type_desc_1'}
        mock_destroy.side_effect = return_volume_types_destroy

        req = fakes.HTTPRequest.blank('/v2/fake/types/1',
                                      use_admin_context=False)
        self.assertEqual(0, len(self.notifier.notifications))
        self.controller._delete(req, 1)
        self.assertEqual(1, len(self.notifier.notifications))
        # non policy authorized user fails to delete type
        mock_policy_enforce.side_effect = (
            exception.PolicyNotAuthorized(action='type_delete'))
        self.assertRaises(exception.PolicyNotAuthorized,
                          self.controller._delete,
                          req, 1)

    def test_create(self):
        self.stubs.Set(volume_types, 'create',
                       return_volume_types_create)
        self.stubs.Set(volume_types, 'get_volume_type_by_name',
                       return_volume_types_get_by_name)

        body = {"volume_type": {"name": "vol_type_1",
                                "os-volume-type-access:is_public": True,
                                "extra_specs": {"key1": "value1"}}}
        req = fakes.HTTPRequest.blank('/v2/fake/types')

        self.assertEqual(0, len(self.notifier.notifications))
        res_dict = self.controller._create(req, body)

        self.assertEqual(1, len(self.notifier.notifications))
        self._check_test_results(res_dict, {
            'expected_name': 'vol_type_1', 'expected_desc': 'vol_type_desc_1'})

    @mock.patch('cinder.volume.volume_types.create')
    @mock.patch('cinder.volume.volume_types.get_volume_type_by_name')
    def test_create_with_description_of_zero_length(
            self, mock_get_volume_type_by_name, mock_create_type):
        mock_get_volume_type_by_name.return_value = \
            {'extra_specs': {"key1": "value1"},
             'id': 1,
             'name': u'vol_type_1',
             'description': u''}

        type_description = ""
        body = {"volume_type": {"name": "vol_type_1",
                                "description": type_description,
                                "extra_specs": {"key1": "value1"}}}
        req = fakes.HTTPRequest.blank('/v2/fake/types')

        res_dict = self.controller._create(req, body)

        self._check_test_results(res_dict, {
            'expected_name': 'vol_type_1', 'expected_desc': ''})

    def test_create_type_with_name_too_long(self):
        type_name = 'a' * 256
        body = {"volume_type": {"name": type_name,
                                "extra_specs": {"key1": "value1"}}}
        req = fakes.HTTPRequest.blank('/v2/fake/types')
        self.assertRaises(exception.InvalidInput,
                          self.controller._create, req, body)

    def test_create_type_with_description_too_long(self):
        type_description = 'a' * 256
        body = {"volume_type": {"name": "vol_type_1",
                                "description": type_description,
                                "extra_specs": {"key1": "value1"}}}
        req = fakes.HTTPRequest.blank('/v2/fake/types')
        self.assertRaises(exception.InvalidInput,
                          self.controller._create, req, body)

    def test_create_duplicate_type_fail(self):
        self.stubs.Set(volume_types, 'create',
                       return_volume_types_create_duplicate_type)
        self.stubs.Set(volume_types, 'get_volume_type_by_name',
                       return_volume_types_get_by_name)

        body = {"volume_type": {"name": "vol_type_1",
                                "extra_specs": {"key1": "value1"}}}
        req = fakes.HTTPRequest.blank('/v2/fake/types')
        self.assertRaises(webob.exc.HTTPConflict,
                          self.controller._create, req, body)

    def test_create_type_with_invalid_is_public(self):
        body = {"volume_type": {"name": "vol_type_1",
                                "os-volume-type-access:is_public": "fake",
                                "description": "test description",
                                "extra_specs": {"key1": "value1"}}}
        req = fakes.HTTPRequest.blank('/v2/fake/types')
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller._create, req, body)

    def _create_volume_type_bad_body(self, body):
        req = fakes.HTTPRequest.blank('/v2/fake/types')
        req.method = 'POST'
        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller._create, req, body)

    def test_create_no_body(self):
        self._create_volume_type_bad_body(body=None)

    def test_create_missing_volume(self):
        body = {'foo': {'a': 'b'}}
        self._create_volume_type_bad_body(body=body)

    def test_create_malformed_entity(self):
        body = {'volume_type': 'string'}
        self._create_volume_type_bad_body(body=body)

    @mock.patch('cinder.volume.volume_types.create')
    @mock.patch('cinder.volume.volume_types.get_volume_type_by_name')
    @mock.patch('cinder.policy.enforce')
    def test_create_with_none_admin(self, mock_policy_enforce,
                                    mock_get_volume_type_by_name,
                                    mock_create_type):

        # allow policy authorized user to create type
        mock_policy_enforce.return_value = None
        mock_get_volume_type_by_name.return_value = \
            {'extra_specs': {"key1": "value1"},
             'id': 1,
             'name': u'vol_type_1',
             'description': u'vol_type_desc_1'}

        body = {"volume_type": {"name": "vol_type_1",
                                "os-volume-type-access:is_public": True,
                                "extra_specs": {"key1": "value1"}}}
        req = fakes.HTTPRequest.blank('/v2/fake/types',
                                      use_admin_context=False)

        self.assertEqual(0, len(self.notifier.notifications))
        res_dict = self.controller._create(req, body)

        self.assertEqual(1, len(self.notifier.notifications))
        self._check_test_results(res_dict, {
            'expected_name': 'vol_type_1', 'expected_desc': 'vol_type_desc_1'})

        # non policy authorized user fails to create type
        mock_policy_enforce.side_effect = (
            exception.PolicyNotAuthorized(action='type_create'))
        self.assertRaises(exception.PolicyNotAuthorized,
                          self.controller._create,
                          req, body)

    @mock.patch('cinder.volume.volume_types.update')
    @mock.patch('cinder.volume.volume_types.get_volume_type')
    def test_update(self, mock_get, mock_update):
        mock_get.return_value = return_volume_types_get_volume_type_updated(
            '1', is_public=False)

        body = {"volume_type": {"name": "vol_type_1_1",
                                "description": "vol_type_desc_1_1",
                                "is_public": False}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        req.method = 'PUT'

        self.assertEqual(0, len(self.notifier.notifications))
        res_dict = self.controller._update(req, '1', body)
        self.assertEqual(1, len(self.notifier.notifications))
        self._check_test_results(res_dict,
                                 {'expected_desc': 'vol_type_desc_1_1',
                                  'expected_name': 'vol_type_1_1',
                                  'is_public': False})

    @mock.patch('cinder.volume.volume_types.update')
    @mock.patch('cinder.volume.volume_types.get_volume_type')
    def test_update_type_with_description_having_length_zero(
            self, mock_get_volume_type, mock_type_update):

        mock_get_volume_type.return_value = \
            {'id': 1, 'name': u'vol_type_1', 'description': u''}

        type_description = ""
        body = {"volume_type": {"description": type_description}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        req.method = 'PUT'
        resp = self.controller._update(req, '1', body)
        self._check_test_results(resp,
                                 {'expected_desc': '',
                                  'expected_name': 'vol_type_1'})

    def test_update_type_with_name_too_long(self):
        type_name = 'a' * 256
        body = {"volume_type": {"name": type_name,
                                "description": ""}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        req.method = 'PUT'
        self.assertRaises(exception.InvalidInput,
                          self.controller._update, req, '1', body)

    def test_update_type_with_description_too_long(self):
        type_description = 'a' * 256
        body = {"volume_type": {"description": type_description}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        req.method = 'PUT'
        self.assertRaises(exception.InvalidInput,
                          self.controller._update, req, '1', body)

    @mock.patch('cinder.volume.volume_types.get_volume_type')
    @mock.patch('cinder.volume.volume_types.update')
    def test_update_non_exist(self, mock_update, mock_get_volume_type):
        mock_get_volume_type.side_effect = exception.VolumeTypeNotFound(
            volume_type_id=777)

        body = {"volume_type": {"name": "vol_type_1_1",
                                "description": "vol_type_desc_1_1"}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/777')
        req.method = 'PUT'

        self.assertEqual(0, len(self.notifier.notifications))
        self.assertRaises(webob.exc.HTTPNotFound,
                          self.controller._update, req, '777', body)
        self.assertEqual(1, len(self.notifier.notifications))

    @mock.patch('cinder.volume.volume_types.get_volume_type')
    @mock.patch('cinder.volume.volume_types.update')
    def test_update_db_fail(self, mock_update, mock_get_volume_type):
        mock_update.side_effect = exception.VolumeTypeUpdateFailed(id='1')
        mock_get_volume_type.return_value = stub_volume_type(1)

        body = {"volume_type": {"name": "vol_type_1_1",
                                "description": "vol_type_desc_1_1"}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        req.method = 'PUT'

        self.assertEqual(0, len(self.notifier.notifications))
        self.assertRaises(webob.exc.HTTPInternalServerError,
                          self.controller._update, req, '1', body)
        self.assertEqual(1, len(self.notifier.notifications))

    def test_update_no_name_no_description(self):
        body = {"volume_type": {}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        req.method = 'PUT'

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller._update, req, '1', body)

    def test_update_empty_name(self):
        body = {"volume_type": {"name": "  ",
                                "description": "something"}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        req.method = 'PUT'

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller._update, req, '1', body)

    @mock.patch('cinder.volume.volume_types.get_volume_type')
    @mock.patch('cinder.db.volume_type_update')
    @mock.patch('cinder.quota.VolumeTypeQuotaEngine.'
                'update_quota_resource')
    def test_update_only_name(self, mock_update_quota,
                              mock_update, mock_get):
        mock_get.return_value = return_volume_types_get_volume_type_updated(
            '999')

        ctxt = context.RequestContext('admin', 'fake', True)
        body = {"volume_type": {"name": "vol_type_999"}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/999')
        req.method = 'PUT'
        req.environ['cinder.context'] = ctxt

        self.assertEqual(0, len(self.notifier.notifications))
        res_dict = self.controller._update(req, '999', body)
        self.assertEqual(1, len(self.notifier.notifications))
        mock_update_quota.assert_called_once_with(ctxt, 'vol_type_999_999',
                                                  'vol_type_999')
        self._check_test_results(res_dict,
                                 {'expected_name': 'vol_type_999_999',
                                  'expected_desc': 'vol_type_desc_999'})

    @mock.patch('cinder.volume.volume_types.update')
    @mock.patch('cinder.volume.volume_types.get_volume_type')
    def test_update_only_description(self, mock_get, mock_update):
        mock_get.return_value = return_volume_types_get_volume_type_updated(
            '888')

        body = {"volume_type": {"description": "vol_type_desc_888_888"}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/888')
        req.method = 'PUT'

        self.assertEqual(0, len(self.notifier.notifications))
        res_dict = self.controller._update(req, '888', body)
        self.assertEqual(1, len(self.notifier.notifications))
        self._check_test_results(res_dict,
                                 {'expected_name': 'vol_type_888',
                                  'expected_desc': 'vol_type_desc_888_888'})

    @mock.patch('cinder.volume.volume_types.update')
    @mock.patch('cinder.volume.volume_types.get_volume_type')
    def test_update_only_is_public(self, mock_get, mock_update):
        is_public = False
        mock_get.return_value = return_volume_types_get_volume_type_updated(
            '123', is_public=is_public)

        body = {"volume_type": {"is_public": is_public}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/123')
        req.method = 'PUT'

        self.assertEqual(0, len(self.notifier.notifications))
        res_dict = self.controller._update(req, '123', body)
        self.assertEqual(1, len(self.notifier.notifications))
        self._check_test_results(res_dict,
                                 {'expected_name': 'vol_type_123_123',
                                  'expected_desc': 'vol_type_desc_123_123',
                                  'is_public': False})

    def test_update_invalid_is_public(self):
        body = {"volume_type": {"name": "test",
                                "description": "something",
                                "is_public": "fake"}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        req.method = 'PUT'

        self.assertRaises(webob.exc.HTTPBadRequest,
                          self.controller._update, req, '1', body)

    @mock.patch('cinder.volume.volume_types.update')
    @mock.patch('cinder.volume.volume_types.get_volume_type')
    def test_rename_existing_name(self, mock_get, mock_update):
        mock_update.side_effect = exception.VolumeTypeExists(
            id="666", name="vol_type_666")
        mock_get.return_value = return_volume_types_get_volume_type_updated(
            '666')
        # first attempt fail
        body = {"volume_type": {"name": "vol_type_666"}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/666')
        req.method = 'PUT'

        self.assertEqual(0, len(self.notifier.notifications))
        self.assertRaises(webob.exc.HTTPConflict,
                          self.controller._update, req, '666', body)
        self.assertEqual(1, len(self.notifier.notifications))

        # delete
        self.notifier.reset()
        self.stubs.Set(volume_types, 'destroy',
                       return_volume_types_destroy)

        req = fakes.HTTPRequest.blank('/v2/fake/types/1')
        self.assertEqual(0, len(self.notifier.notifications))
        self.controller._delete(req, '1')
        self.assertEqual(1, len(self.notifier.notifications))

        # update again
        mock_update.side_effect = mock.MagicMock()
        body = {"volume_type": {"name": "vol_type_666_666"}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/666')
        req.method = 'PUT'

        self.notifier.reset()
        self.assertEqual(0, len(self.notifier.notifications))
        res_dict = self.controller._update(req, '666', body)
        self._check_test_results(res_dict,
                                 {'expected_name': 'vol_type_666',
                                  'expected_desc': 'vol_type_desc_666'})
        self.assertEqual(1, len(self.notifier.notifications))

    @mock.patch('cinder.volume.volume_types.update')
    @mock.patch('cinder.volume.volume_types.get_volume_type')
    @mock.patch('cinder.policy.enforce')
    def test_update_with_non_admin(self, mock_policy_enforce, mock_get,
                                   mock_update):

        # allow policy authorized user to update type
        mock_policy_enforce.return_value = None
        mock_get.return_value = return_volume_types_get_volume_type_updated(
            '1', is_public=False)

        body = {"volume_type": {"name": "vol_type_1_1",
                                "description": "vol_type_desc_1_1",
                                "is_public": False}}
        req = fakes.HTTPRequest.blank('/v2/fake/types/1',
                                      use_admin_context=False)
        req.method = 'PUT'

        self.assertEqual(0, len(self.notifier.notifications))
        res_dict = self.controller._update(req, '1', body)
        self.assertEqual(1, len(self.notifier.notifications))
        self._check_test_results(res_dict,
                                 {'expected_desc': 'vol_type_desc_1_1',
                                  'expected_name': 'vol_type_1_1',
                                  'is_public': False})

        # non policy authorized user fails to update type
        mock_policy_enforce.side_effect = (
            exception.PolicyNotAuthorized(action='type_update'))
        self.assertRaises(exception.PolicyNotAuthorized,
                          self.controller._update,
                          req, '1', body)

    def _check_test_results(self, results, expected_results):
        self.assertEqual(1, len(results))
        self.assertEqual(expected_results['expected_desc'],
                         results['volume_type']['description'])
        if expected_results.get('expected_name'):
            self.assertEqual(expected_results['expected_name'],
                             results['volume_type']['name'])
        if expected_results.get('is_public') is not None:
            self.assertEqual(expected_results['is_public'],
                             results['volume_type']['is_public'])
