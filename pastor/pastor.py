#!/usr/bin/env python
import sys
import botohelper
import random
import time
import sshmaster
import vmtools
from string import Template

vm_root_path = vmtools.vm_root_grabber()
sys.path.append(vm_root_path)
from local_settings import *

class CreateResource():
    """Class to create aws resources

    public methods:
    create_saltmater_vpc
    execute_remote_resources
    get_latest_ami

    instance variables:
    self.aws_profile
    self.aws_region
    self.ec2
    self.iam
    self.route53
    self.ami_id
    """

    def __init__(self, aws_profile, aws_region, environment='dev'):
        """set instance variables, create botohelper instances

        keyword arguments:
        :type aws_profile: string
        :param aws_profile: the profile to use from ~/.aws/credentials to connect to aws
        :type aws_region: string
        :param aws_region: the region to use for the aws connection object (all resources will be created in this region)
        :type environment: string
        :param environment: the enviroment tag for the vpc defaults to dev
        """
        self.aws_profile = aws_profile
        self.aws_region = aws_region
        self.environment = environment
        # aws botohelper ec2 session
        self.ec2 = botohelper.ec2.Ec2(aws_profile=self.aws_profile, aws_region=self.aws_region)
        self.iam = botohelper.iam.Iam(aws_profile=self.aws_profile, aws_region=self.aws_region)
        self.route53 = botohelper.route53.Route53(aws_profile=self.aws_profile, aws_region=self.aws_region)
        # assumes that AMI_NAME_PREFIX is set in local_settings.py
        self.ami_id = self.ec2.get_latest_ami_from_prefix(ami_name_prefix=AMI_NAME_PREFIX).image_id
        self.default_saltmaster_instance_size = DEFAULT_SALTMASTER_INSTANCE_SIZE
        # get environment dict
        self.environment_dict = ENVIRONMENT_DICT[self.environment]
        if 'saltmaster_instance_profile_arn' in self.environment_dict:
            self.saltmaster_instance_profile_arn = self.environment_dict['saltmaster_instance_profile_arn']
        else:
            self.saltmaster_instance_profile_arn = None

    def create_saltmater_vpc(self, vpc_name, cidr_block):
        """Create a vpc with a saltmaster instance inside it, return vpc object
        keyword arguments:
        :type vpc_name: string
        :param vpc_name: the Name tag for the vpc
        :type cidr_block: string
        :param cidr_block: cidr_block for the new vpc (ex '10.0.1.0/24')
        """
        # create a basic vpc
        vpc_object_dict = self.ec2.create_vpc(vpc_name=vpc_name, cidr_block=cidr_block, environment=self.environment)
        # subnet name
        subnet_name='{}_default_subnet'.format(vpc_name)
        # choose random availability zone for subnet
        subnet_availability_zone = random.choice(self.ec2.availability_zones_list)
        # create a default subnet with the same cidr block as the vpc
        subnet = self.ec2.create_subnet(vpc_object=vpc_object_dict['vpc_object'], subnet_name=subnet_name, cidr_block=cidr_block, availability_zone=subnet_availability_zone)
        vpc_object_dict['saltmater_subnet'] = subnet
        # associate default route table with subnet and internet gateway
        vpc_object_dict['default_route_table'].associate_with_subnet(SubnetId=subnet.subnet_id)
        vpc_object_dict['default_route_table'].create_route(DestinationCidrBlock='0.0.0.0/0',GatewayId=vpc_object_dict['internet_gateway'].internet_gateway_id)
        # open port 22 up on default security group
        vpc_object_dict['default_security_group'].authorize_ingress(IpProtocol='tcp', FromPort=22, ToPort=22, CidrIp='0.0.0.0/0')
        # compile saltmaster instance name
        saltmaster_instance_name = 'saltmaster-{}.{}'.format(vpc_name, self.environment_dict['domain'])
        # create saltmaster instance
        saltmaster_instance_object = self.ec2.create_instance(instance_name=saltmaster_instance_name, subnet_id=vpc_object_dict['saltmater_subnet'].subnet_id, keypair_name=self.environment_dict['keypair_name'], ami_id=self.ami_id, instance_size=self.default_saltmaster_instance_size, public_ip=True, instance_profile_arn=self.saltmaster_instance_profile_arn)
        # wait until instance is running
        saltmaster_instance_object.wait_until_running()
        print('public_ip',saltmaster_instance_object.public_ip_address)
        print('private_ip',saltmaster_instance_object.private_ip_address)
        #real_time_saltmaster_object = self.ec2.get_object_from_name(tag_name=saltmaster_instance_name, object_type='instance')
        #while real_time_saltmaster_object.state['Name'] != 'running':
        #    time.sleep(5)
        #    real_time_saltmaster_object = self.ec2.get_object_from_name(tag_name=saltmaster_instance_name, object_type='instance')
        # dns saltmaster instance
        # public dns
        self.route53.modify_a_record(fqdn=saltmaster_instance_name, ip_address=saltmaster_instance_object.public_ip_address, ttl=60)
        # private dns
        self.route53.modify_a_record(fqdn=saltmaster_instance_name, ip_address=saltmaster_instance_object.private_ip_address, ttl=60, zone_group_type='private_zones')
        # push files to saltmaster and execute remote commands
        self.execute_remote_resources(list_of_resources=SALTMASTER_SETUP_LIST, hostip=saltmaster_instance_object.public_ip_address, templating_dict={'saltmasterhostname': saltmaster_instance_name})
        # return vpc_object_dict
        vpc_object_dict['saltmaster_instance_object'] = saltmaster_instance_object
        return vpc_object_dict
   
    def execute_remote_resources(self, list_of_resources, hostip, templating_dict={}):
        """Take list_of_resources, hostip, hostname, and optionally environment step through list_of_resources and execute the command or create the file
        keyword arguments:
        :type list_of_resources: list
        :param list_of_resources: a list of dictionaries that describe files to create or commands to run. An example of a list with a three dictionaries is provided. Resources are created/executed in order. Files can be created by referencing a file on the local filesystem (if the key 'local_file_path' is present) or providing the file content (if the key 'file_content' is present) in the dictionary (note: if 'local_file_path' is present, 'file_content' is ignored):
        [ { 'resource_type': 'file', 'remote_file_path': '/root/.ssh/private_key', 'file_mode' : 600, 'file_owner': 'root', 'local_file_path': LOCAL_FILE_DIRECTORY+'private_key' }, { 'resource_type': 'command', 'remote_command': 'mkdir -p /tmp/salt_temp_dir' }, { 'resource_type': 'file', 'remote_file_path': '/tmp/salt_temp_dir/saltmaster.conf', 'file_mode' : 644, 'file_owner': 'root', 'file_content': 'master: $saltmasterhostname' }, ]
        :type hostip: string
        :param hostip: the ip of the host where to execute/create the resources
        :type templating_dict: dict
        :param templating_dict: optional: a dictionary of variable names (strings only, note: do not begin string with a $ in the temlating_dict) and values (strings only). If a key in the templating_dict matches a string, that is prefixed with a dollar sign ($), from the value of a 'file_content' or 'remote_command' key in a dictionary from the list_of_resources, then the value of the key in the templating_dict will be substitued. An example templating_dict: { 'saltmasterhostname': 'saltmaster-vpc1.domain.com' } if used with the above example for list_of_resources the file contents for the file /tmp/salt_temp_dir/saltmaster.conf would be: 'master: saltmaster-vpc1.domain.com'
        """
        # step through the list_of_resources and create the file or execute the command
        for resource_dict in list_of_resources:
            if resource_dict['resource_type'] == 'file':
                # if we have a local copy scp it up to remote host
                if 'local_file_path' in resource_dict:
                    sshmaster.scp_cmd_multi_try(current_host=hostip, mode='put', username=SSH_SETUP_DICT['username'], local_file=resource_dict['local_file_path'], remote_file=resource_dict['remote_file_path'], keyfile=self.environment_dict['keypair_path'], file_owner=resource_dict['file_owner'], file_mode=resource_dict['file_mode'], use_sudo=SSH_SETUP_DICT['use_sudo'], print_stdout=SSH_SETUP_DICT['debug'], debug=SSH_SETUP_DICT['debug'])
                # if we have file contents create new file on remote host
                elif 'file_content' in resource_dict:
                    # subsitute any variables that match keys in our templating_dict
                    resource_dict['file_content'] = Template(resource_dict['file_content']).safe_substitute(templating_dict)
                    sshmaster.create_remote_file_multi_try(current_host=hostip, username=SSH_SETUP_DICT['username'], keyfile=self.environment_dict['keypair_path'], file_location=resource_dict['remote_file_path'], file_contents=resource_dict['file_content'], file_mode=resource_dict['file_mode'], file_owner=resource_dict['file_owner'], use_sudo=SSH_SETUP_DICT['use_sudo'], print_stdout=SSH_SETUP_DICT['debug'], debug=SSH_SETUP_DICT['debug'])
            elif resource_dict['resource_type'] == 'command':
                # subsitute any variables that match keys in our templating_dict
                resource_dict['remote_command'] = Template(resource_dict['remote_command']).safe_substitute(templating_dict)
                sshmaster.ssh_cmd(current_host=hostip, command=resource_dict['remote_command'], username=SSH_SETUP_DICT['username'], keyfile=self.environment_dict['keypair_path'], print_stdout=SSH_SETUP_DICT['debug'], use_sudo=SSH_SETUP_DICT['use_sudo'])


