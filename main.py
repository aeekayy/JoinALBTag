#!/usr/bin/python

import boto3
import json
import re
import requests

def get_region():
	res = requests.get('http://169.254.169.254/latest/dynamic/instance-identity/document')
	res_json = json.loads(res.content)
	return res_json['region']

def get_instance_id():
	res = requests.get('http://169.254.169.254/latest/meta-data/instance-id')
	return res.content

def get_instance_type():
	res = requests.get('http://169.254.169.254/latest/meta-data/inctance-type')
	return res.content

# Import EC2 for Boto3
def get_instance_tags(fid, tags, region):
	ec2 = boto3.resource('ec2', region_name=region)
	ec2instance = ec2.Instance(fid)
	ec2tags = {}

	# Get a list from the tags parameter
	i_tags = [ x for x in re.compile('\s*[,|\s+]\s*').split(tags) ]

	# iterate through the tags and get the values to the tag names
	for tag in ec2instance.tags:
		if tag["Key"] in i_tags:
			ec2tags[tag["Key"]] = tag["Value"]

	return ec2tags

def get_alb_by_tags(tags, region):
	# get the alb boto3 object
	resource_tags = boto3.client('resourcegroupstaggingapi', region_name=region)
	search_tags = []

	# prepare the filter string
	for tag in tags:
		t_tag = {}
		t_tag['Key'] = tag
		t_tag['Values'] = [ tags.get(tag) ]
		search_tags.append(t_tag)

	# Get the resources by tag
	albs = resource_tags.get_resources(TagFilters=search_tags, ResourceTypeFilters = [ "elasticloadbalancing:loadbalancer" ])
	alb = (albs['ResourceTagMappingList']).pop()
	return alb['ResourceARN']

def register_targets(alb_arn, instance_id, region):
	# Get the ALB target groups
	alb_client = boto3.client('elbv2', region_name=region)

	target_groups_res = alb_client.describe_target_groups(LoadBalancerArn=alb_arn)
	target_groups = target_groups_res['TargetGroups']

	# Join the target groups
	for target in target_groups:
		print "Joining target group: "
		print target['TargetGroupArn']
		response = alb_client.register_targets( TargetGroupArn=target['TargetGroupArn'], Targets=[ { 'Id': instance_id } ] )

	print "Done adding this instance to the target groups."

def main():
	# get the region
	aws_region = get_region()

	# get the instance id
	instance_id = get_instance_id()

	# get the instance tags and values
	instance_tags = get_instance_tags(instance_id, "Environment,Role,Project", aws_region)
	print "The tag values are..."
	print instance_tags

	# find the ALB with the same tags
	alb_instance = get_alb_by_tags(instance_tags, aws_region)
	print "The ALB has been found. Joining..."
	print alb_instance

	# Add the instance to the ALB
	register_targets(alb_instance, instance_id, aws_region)

main()
