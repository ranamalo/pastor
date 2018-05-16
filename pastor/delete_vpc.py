#!/usr/bin/env python
import datetime
import os
import sys
import argparse
import botohelper
from termcolor import cprint

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
parser = argparse.ArgumentParser(description="A tool to delete vpcs by name.")
parser.add_argument('-p', '--aws-profile', help="which aws profile to use from ~/.aws/credentials", required=True, dest='aws_profile', action='store')
parser.add_argument('-r', '--aws-region', help="the vpc's region", required=True, dest='aws_region', action='store')
parser.add_argument('-n', '--vpc-name', help='the name of the vpc', required=True, dest='vpc_name', action='store')
#parser.add_argument('-e', '--environment', help='Optional: the enviroment dev or prod (defaults to dev)', required=False, dest='environment', default='dev', action='store')
# parse the options
args = parser.parse_args()

# create the aws connection object
ec2 = botohelper.ec2.Ec2(aws_profile=args.aws_profile, aws_region=args.aws_region)
# delete the vpc
ec2.delete_vpc(vpc_name=args.vpc_name)
