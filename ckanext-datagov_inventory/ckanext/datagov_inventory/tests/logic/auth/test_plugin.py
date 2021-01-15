"""Tests for datagov_inventory plugin.py."""

from nose.tools import assert_raises
from nose.tools import assert_equal
from nose.tools import assert_raises_regexp

import ckan.model as model
from ckan.plugins.toolkit import NotAuthorized, ObjectNotFound
import ckan.tests.factories as factories
import ckan.logic as logic
import mock

import ckan.tests.helpers as helpers


class TestDatagovInventoryAuth(object):

    def test_user_update_user_cannot_update_another_user(self):
        '''Users should not be able to update other users' accounts.'''

        # 1. Setup.

        # Make a mock ckan.model.User object, Fred.
        fred = factories.MockUser(name='fred')

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()
        # model.User.get(user_id) should return Fred.
        mock_model.User.get.return_value = fred

        # Put the mock model in the context.
        # This is easier than patching import ckan.model.
        context = {'model': mock_model}

        # The logged-in user is going to be Bob, not Fred.
        context['user'] = 'bob'

        # 2. Call the function that's being tested, once only.

        # Make Bob try to update Fred's user account.
        params = {
            'id': fred.id,
            'name': 'updated_user_name',
        }

        # 3. Make assertions about the return value and/or side-effects.

        assert_raises(logic.NotAuthorized, helpers.call_auth,
                      'user_update', context=context, **params)

        # 4. Do nothing else!

    def test_logged_in_user_access_to_package_show(self):
        #user_dict = helpers.call_action('user_create', name='test_user',
        #                email='test_user@nospam.com', password='password')

        fred = factories.MockUser(name='fred')

        # Make a mock ckan.model object.
        mock_model = mock.MagicMock()
        # model.User.get(user_id) should return Fred.
        mock_model.User.get.return_value = fred

        # Put the mock model in the context.
        # This is easier than patching import ckan.model.               
        context = {
           'model': mock_model,
           'ignore_auth': False,
           'user': 'fred'
        }
        params = {
           'id': 'test-dataset-1'
        }
        #resource = factories.Resource(**params)
        #helpers.call_action('package_show', context, **params)
        #assert_raises(logic.NotAuthorized, helpers.call_auth, 'package_show', **params)

        #NotAuthorized: User fred not authorized to read package <MagicMock name='mock.Package.get().id' id='140584650135760'>
        assert_raises_regexp(logic.NotAuthorized, 'User fred not authorized to read package.*')
        """with assert_raises(logic.NotAuthorized) as e:
            logic.check_access('package_show',{'user': 'fred'}, {'id': 'test-dataset-1'})
        assert_equal(e.exception.message, 'User %s not authorized to read package %s' % (context['user'], mock_model.Package.get().id ))

        with assert_raises_regexp(logic.NotAuthorized, 'User fred not authorized to read package.*') as e:
            logic.check_access('package_show',{'user': 'fred'}, {'id': 'test-dataset-1'})
        assert_raises_reqequal(e.exception.message, 'User fred not authorized to read package.*')"""



"""
    def test_logged_in_user_access(self):
        app = self._get_test_app()

        user_dict = call_action('user_create', name='test_user',
                        email='test_user@nospam.com', password='pass')

        context = {
            'ignore_auth': False,
            'user': user_dict['name']
        }                

        result = helpers.call_auth('package_show', context=context,
                           id='some_user_id',
                           name='updated_user_name')
      """
