#   Foremast - Pipeline Tooling
#
#   Copyright 2016 Gogo, LLC
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
"""Test IAM Policy construction."""
from unittest import mock

from foremast.iam.create_iam import create_iam_resources

EC2_TEMPLATE_NAME = 'infrastructure/iam/ec2_role_policy.json.j2'
LAMBDA_TEMPLATE_NAME = 'infrastructure/iam/lambda_role_policy.json.j2'


@mock.patch('foremast.iam.create_iam.attach_profile_to_role')
@mock.patch('foremast.iam.create_iam.boto3.session.Session')
@mock.patch('foremast.iam.create_iam.construct_policy')
@mock.patch('foremast.iam.create_iam.get_details')
@mock.patch('foremast.iam.create_iam.get_properties')
@mock.patch('foremast.iam.create_iam.resource_action')
def test_create_iam_resources(resource_action, get_properties, get_details, construct_policy, session,
                              attach_profile_to_role):
    """Check basic functionality."""
    get_details.return_value.iam.return_value = {'group': 1, 'policy': 2, 'profile': 3, 'role': 4, 'user': 5}
    get_properties.return_value = {'type': 'ec2'}

    assert create_iam_resources(env='narnia', app='lion/aslan')

    assert resource_action.call_count == 6
    session.assert_called_with(profile_name='narnia')
    get_details.assert_called_with(env='narnia', app='lion/aslan')
    get_properties.assert_called_with(env='pipeline')
    construct_policy.assert_called_with(app='lion/aslan', group=1, env='narnia', pipeline_settings=get_properties.return_value)


@mock.patch('foremast.iam.create_iam.attach_profile_to_role')
@mock.patch('foremast.iam.create_iam.boto3.session.Session')
@mock.patch('foremast.iam.create_iam.construct_policy')
@mock.patch('foremast.iam.create_iam.get_details')
@mock.patch('foremast.iam.create_iam.get_properties')
@mock.patch('foremast.iam.create_iam.get_template')
@mock.patch('foremast.iam.create_iam.resource_action')
def test_iam_role_policy(resource_action, get_template, get_properties, get_details, construct_policy, session,
                         attach_profile_to_role):
    """IAM Role Policy should match deployment type."""
    get_properties.return_value = {'type': 'ec2'}
    get_details.return_value.iam.return_value = {'group': 1, 'policy': 2, 'profile': 3, 'role': 4, 'user': 5}

    assert create_iam_resources()

    get_template.assert_called_with(EC2_TEMPLATE_NAME)
    calls = [mock.call(
        mock.ANY,
        action='create_role',
        log_format=mock.ANY,
        RoleName=mock.ANY,
        AssumeRolePolicyDocument=get_template.return_value)]
    resource_action.assert_has_calls(calls)
