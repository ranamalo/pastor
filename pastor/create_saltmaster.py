#!/usr/bin/env python
import datetime
import os
import sys
import argparse
from termcolor import cprint
from pastor import CreateResource

import vmtools

vm_root_path = vmtools.vm_root_grabber()
sys.path.append(vm_root_path)
from local_settings import *

# get today's date
today_raw = datetime.datetime.now()
today = today_raw.strftime("%Y%m%d")
today_extended = today_raw.strftime("%Y%m%d%H%M%S")
todaymonth = today_raw.strftime("%Y%m")

# get options 
#parser = optparse.OptionParser()
parser = argparse.ArgumentParser(description="A tool to create a saltmaster vpc and all.")
parser.add_argument('-p', '--aws-profile', help="which aws profile to use from ~/.aws/credentials", required=True, dest='aws_profile', action='store')
parser.add_argument('-r', '--aws-region', help='the region in which to create the vpc and saltmaster', required=True, dest='aws_region', action='store')
parser.add_argument('-n', '--vpc-name', help='the name for the new vpc', required=True, dest='vpc_name', action='store')
parser.add_argument('-c', '--cidr-block', help='the CIDR block for the new vpc (the default subnet will be created with this entire CIDR block)', required=True, dest='cidr_block', action='store')
parser.add_argument('-e', '--environment', help='Optional: the enviroment dev or prod (defaults to dev)', required=False, dest='environment', default='dev', action='store')
# parse the options
args = parser.parse_args()

# make sure we don't have any underscores in vpc_name
if '_' in args.vpc_name:
    underscore_error_message = 'ERROR: underscores are not allowed in vpc_name because they are an invalid character for hostnames (the hostname is constructed from vpc_name)'
    cprint(underscore_error_message, 'red')
    parser.print_help()
    sys.exit(1)

# create the aws connection object
aws_connection_object = CreateResource(aws_profile=args.aws_profile, aws_region=args.aws_region, environment=args.environment)
# create the vpc for the saltmaster
vpc_object_dict = aws_connection_object.create_saltmater_vpc(vpc_name=args.vpc_name, cidr_block=args.cidr_block)

# get the Name tag directly from the vpc in aws (double check)
vpc_name_from_vpc_object = ''
for tag_dict in vpc_object_dict['vpc_object'].tags:
    if tag_dict['Key'] == 'Name':
        vpc_name_from_vpc_object = tag_dict['Value']
        break
# get the Name tag directly from the instance in aws (double check)
instance_name_from_vpc_object = ''
for tag_dict in vpc_object_dict['saltmaster_instance_object'].tags:
    if tag_dict['Key'] == 'Name':
        instance_name_from_vpc_object = tag_dict['Value']
        break

# feedback on correct naming checks above
if vpc_name_from_vpc_object and instance_name_from_vpc_object:
    vpc_creation_result_message = 'Vpc: {} created with name: {}'.format(vpc_object_dict['vpc_object'].vpc_id, vpc_name_from_vpc_object)
    instance_creation_result_message = 'Saltmaster instance: {} created with name: {} ip: {}'.format(vpc_object_dict['saltmaster_instance_object'].instance_id, instance_name_from_vpc_object, vpc_object_dict['saltmaster_instance_object'].public_ip_address)
else:
    vpc_creation_result_message = 'Failed to find a name for vpc: {}'.format(vpc_object_dict['vpc_object'].vpc_id)
print(vpc_creation_result_message)
print(instance_creation_result_message)




