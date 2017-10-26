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
"""Get available Subnets for specific Targets."""
import logging
from collections import defaultdict, namedtuple
from pprint import pformat

import requests
from tryagain import retries

from ..consts import API_URL, GATE_CA_BUNDLE, GATE_CLIENT_CERT
from ..exceptions import SpinnakerSubnetError, SpinnakerTimeout

LOG = logging.getLogger(__name__)

SubnetAttributes = namedtuple('SubnetAttributes', [
    'account',
    'availability_zone',
    'subnet_id',
    'subnet_purpose',
    'subnet_region',
])
"""Important Subnet attributes configured in Spinnaker."""


def targeted_subnets(subnets, target='ec2'):
    """Generate Subnets matching ``target`` Provider.

    Args:
        subnets (list): Many :obj:`dict` containing Subnet attributes.
        target (str): Type of subnets to look up (ec2 or elb).

    Yields:
        :obj:`SubnetAttributes`: Subnet attributes matching ``target``.

    """
    for subnet in subnets:
        subnet_attributes = SubnetAttributes(
            account=subnet['account'],
            availability_zone=subnet['availabilityZone'],
            subnet_id=subnet['id'],
            subnet_purpose=subnet['purpose'],
            subnet_region=subnet['region'])

        LOG.debug('Subnet: %s', subnet_attributes)

        if subnet['target'] == target:
            yield subnet_attributes


@retries(max_attempts=6, wait=2.0, exceptions=SpinnakerTimeout)  # noqa
def get_all_subnets():
    """Retrieve list of all Subnets configured in Spinnaker.

    Returns:
        list: Subnet data in :obj:`dict` format::

            [
                {
                    'account': 'test',
                    'availabilityZone': 'us-west-2b',
                    'availableIpAddressCount': 256,
                    'cidrBlock': '0.0.0.0/0',
                    'deprecated': False,
                    'id': 'subnet-00000000',
                    'purpose': 'internal',
                    'region': 'us-west-2',
                    'state': 'available',
                    'target': 'elb',
                    'type': 'aws',
                    'vpcId': 'vpc-00000000',
                }
            ]

    Raises:
        foremast.exceptions.SpinnakerTimeout: Spinnaker failed to respond in
            time.

    """
    subnet_url = '{0}/subnets/aws'.format(API_URL)
    subnet_response = requests.get(subnet_url, verify=GATE_CA_BUNDLE, cert=GATE_CLIENT_CERT)

    if not subnet_response.ok:
        raise SpinnakerTimeout(subnet_response.text)

    subnets = subnet_response.json()
    LOG.debug('Configured Subnets: %s', subnets)
    return subnets


# TODO: split up into get_az, and get_subnet_id
def get_subnets(
        target='ec2',
        purpose='internal',
        env='',
        region='',
):
    """Get all availability zones for a given target.

    Args:
        target (str): Type of subnets to look up (ec2 or elb).
        env (str): Environment to look up.
        region (str): AWS Region to find Subnets for.

    Returns:
        collections.defaultdict: Dictionary of availbility zones.

        If ``region`` is specified, the :obj:`dict` will be structured::

            {'region': ['avaibilityzones']}

        Otherwise, all data will be returned structured as::

            {'account': 'region': ['availabilityzones']}

    """
    result_dict = None

    account_az_dict = defaultdict(defaultdict)
    subnet_id_dict = defaultdict(defaultdict)

    subnet_list = get_all_subnets()

    for account, availability_zone, subnet_id, subnet_purpose, subnet_region in targeted_subnets(
            subnet_list, target=target):
        try:
            account_az_dict[account][subnet_region].add(availability_zone)
        except KeyError:
            account_az_dict[account][subnet_region] = set((availability_zone))

        # get list of all subnet IDs with correct purpose
        if subnet_purpose == purpose:
            try:
                subnet_id_dict[account][subnet_region].append(subnet_id)
            except KeyError:
                subnet_id_dict[account][subnet_region] = [subnet_id]

        LOG.debug('%s regions: %s', account, list(account_az_dict[account].keys()))

    LOG.debug('AZ dict:\n%s', pformat(dict(account_az_dict)))
    result_dict = account_az_dict

    if all([env, region]):
        region_dict = defaultdict(dict)

        try:
            region_dict[region] = account_az_dict[env][region]
        except KeyError:
            LOG.fatal('Missing key while setting Region: %s', account_az_dict)
            raise SpinnakerSubnetError(env=env, region=region)

        try:
            region_dict['subnet_ids'][region] = subnet_id_dict[env][region]
        except KeyError:
            LOG.fatal('Missing key while setting Subnet IDs: %s', subnet_id_dict)
            raise SpinnakerSubnetError(env=env, region=region)

        LOG.debug('Region dict: %s', dict(region_dict))
        result_dict = region_dict

    return result_dict
