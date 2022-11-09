#!/usr/bin/python3

from __future__ import print_function

from troposphere import ec2
from troposphere import Tags, Ref, Sub, Export
from troposphere import Template, Output

template = Template()

vpc = template.add_resource(
    ec2.VPC(
        'VPC',
        CidrBlock="10.0.0.0/24",
        Tags=Tags(
            Name="VPC for troposphere exercise"
        )
    )
)

subnet = ec2.Subnet("TestSubnet")

subnet.AvailabilityZone = "eu-west-3c"
subnet.CidrBlock = "10.0.0.0/24"
subnet.VpcId = Ref(vpc)
subnet.Tags = [
    {"Key" : "Name", "Value" : "Subnet for troposphere exercise"},
    {"Key" : "Zone & Block", "Value" : "eu-west-3c (Paris) & 10.0.0.0/24"}
]

template.add_resource(subnet)

output_subnet = Output("outputSubnet")
output_subnet.Value = Ref(subnet)
output_subnet.Export = Export(Sub("${AWS::StackName}-" + subnet.title))

template.add_output(output_subnet)

with open('troposphere-exercise.yaml','w') as f:
    f.write(template.to_yaml())

with open('troposphere-exercise.json','w') as f:
    f.write(template.to_json())